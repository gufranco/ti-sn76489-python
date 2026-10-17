import collections
import hashlib
import json
import sys
import zipfile
from collections.abc import Callable, Iterator, Mapping
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from typing import Any

from conformance import board

SUFFIXES = (".sg", ".sc", ".sf", ".sms")

GATED_SETS = ("Japan", "Korea", "Taiwan", "Other Regions")

GATED_SUFFIX = ".sg"

NOT_GAMES = ("[BIOS]", "(Beta", "(Proto")

FRAMES = 600

JOBS = 10

RAISES_NOTHING = "the model raises on no image"

NEVER_LOCKS = "the shift register never reaches zero"

EARLY = "writes made before the last byte finished loading"

PROPERTIES = (RAISES_NOTHING, NEVER_LOCKS)

COUNTED = ("first", "second", "noise", "attenuation")

CORPUS = Path(__file__).resolve().parent / "corpus.json"

CORPUS_INDENT = 2

USAGE = "usage: python3 -m conformance.census <path> [path ...] [--frames N] [--jobs N]"

Image = tuple[str, str, bytes]

Distinct = tuple[bool, bytes, str]


def _members(where: Path) -> Iterator[Image]:
    with zipfile.ZipFile(where) as bundle:
        for entry in bundle.infolist():
            if not entry.is_dir() and Path(entry.filename).suffix.lower() in SUFFIXES:
                yield where.name, Path(entry.filename).name, bundle.read(entry)


def images_in(where: Path) -> Iterator[Image]:
    if where.is_dir():
        for path in sorted(where.rglob("*")):
            if path.is_file() and path.suffix.lower() == ".zip":
                yield from _members(path)
            elif path.is_file() and path.suffix.lower() in SUFFIXES:
                yield where.name, path.name, path.read_bytes()
        return
    if where.suffix.lower() == ".zip":
        yield from _members(where)
        return
    if where.suffix.lower() in SUFFIXES:
        yield where.parent.name, where.name, where.read_bytes()


def gated(collection: str, name: str) -> bool:
    retail = any(one in collection for one in GATED_SETS)
    shipped = not any(tag in name for tag in NOT_GAMES)
    return retail and shipped and name.lower().endswith(GATED_SUFFIX)


def _heard(sound: Any, raised: str | None) -> dict[str, Any]:
    heard = getattr(sound, "heard", None) or board.Heard()
    part = getattr(sound, "part", None)
    return {
        "first": sorted(heard.first),
        "second": sorted(heard.second),
        "noise": sorted(heard.noise),
        "attenuation": sorted(heard.attenuation),
        "zero": heard.zero_periods > 0,
        "early": heard.early,
        "writes": heard.writes,
        "locked": part is not None and part.shift == 0,
        "raised": raised,
    }


def examine(
    job: tuple[bytes, int], build: Callable[[bytes], Any] = board.SoundBoard
) -> dict[str, Any]:
    rom, frames = job
    sound = build(rom)
    try:
        sound.run_frames(frames)
    except Exception as error:
        return _heard(sound, f"{type(error).__name__}: {error} at frame {sound.frames}")
    return _heard(sound, None)


def _distinct(paths: list[Path]) -> tuple[int, list[Distinct]]:
    listings = 0
    seen: dict[str, Distinct] = {}
    for where in paths:
        for collection, name, rom in images_in(where):
            listings += 1
            digest = hashlib.sha256(rom).hexdigest()
            held = seen.get(digest)
            seen[digest] = (
                bool(held and held[0]) or gated(collection, name),
                rom,
                name,
            )
    return listings, [seen[digest] for digest in sorted(seen)]


def _results(images: list[Distinct], frames: int, jobs: int) -> list[dict[str, Any]]:
    work = [(rom, frames) for _, rom, _ in images]
    if jobs <= 1:
        return [examine(one) for one in work]
    with ProcessPoolExecutor(max_workers=jobs) as pool:
        return list(pool.map(examine, work))


def _counted(results: list[dict[str, Any]], key: str) -> dict[str, int]:
    held: collections.Counter[int] = collections.Counter()
    for found in results:
        held.update(found[key])
    return {str(value): count for value, count in sorted(held.items())}


def tally(images: list[Distinct], results: list[dict[str, Any]]) -> dict[str, Any]:
    broken = dict.fromkeys(PROPERTIES, 0)
    early = {"retail": 0, "other": 0}
    for (retail, _, _), found in zip(images, results, strict=True):
        early["retail" if retail else "other"] += found["early"]
        broken[RAISES_NOTHING] += found["raised"] is not None
        broken[NEVER_LOCKS] += found["locked"]
    return {
        "properties": broken,
        **{key: _counted(results, key) for key in COUNTED},
        "zeroPeriods": sum(found["zero"] for found in results),
        "writes": sum(found["writes"] for found in results),
        "early": early,
        "silent": sum(not found["writes"] for found in results),
    }


def culprits(images: list[Distinct], results: list[dict[str, Any]]) -> dict[str, list[str]]:
    named: dict[str, list[str]] = {name: [] for name in (*PROPERTIES, EARLY)}
    for (_, _, image), found in zip(images, results, strict=True):
        if found["raised"] is not None:
            named[RAISES_NOTHING].append(f"{image}: {found['raised']}")
        if found["locked"]:
            named[NEVER_LOCKS].append(image)
        if found["early"]:
            named[EARLY].append(f"{image}: {found['early']}")
    return named


def take(paths: list[Path], frames: int = FRAMES, jobs: int = JOBS) -> Mapping[str, Any]:
    listings, images = _distinct(paths)
    results = _results(images, frames, jobs)
    return {
        "listings": listings,
        "images": len(images),
        "gated": sum(1 for retail, _, _ in images if retail),
        "frames": frames,
        **tally(images, results),
        "culprits": culprits(images, results),
    }


def _options(argv: list[str]) -> tuple[list[Path], int, int] | None:
    paths: list[Path] = []
    frames, jobs = FRAMES, JOBS
    rest = list(argv)
    while rest:
        item = rest.pop(0)
        if item in ("--frames", "--jobs"):
            if not rest:
                return None
            value = int(rest.pop(0))
            frames, jobs = (value, jobs) if item == "--frames" else (frames, value)
        else:
            paths.append(Path(item))
    return (paths, frames, jobs) if paths else None


def report(taken: Mapping[str, Any]) -> list[str]:
    named = taken["culprits"]
    lines = [
        f"{taken['listings']} listings, {taken['images']} distinct images, "
        f"{taken['gated']} retail, {taken['frames']} frames each"
    ]
    for name, count in taken["properties"].items():
        lines.append(f"  {'ok  ' if not count else '   !'}  {name}: {count} broken")
        lines.extend(f"         {one}" for one in named[name])
    lines.append(f"  observed  {EARLY}: {len(named[EARLY])} images")
    lines.extend(f"         {one}" for one in named[EARLY])
    return lines


def main(argv: list[str], into: Path = CORPUS) -> int:
    chosen = _options(argv)
    if chosen is None:
        print(USAGE)
        return 2
    paths, frames, jobs = chosen
    for one in paths:
        if not one.exists():
            print(f"absent: {one}")
    taken = take([one for one in paths if one.exists()], frames, jobs)
    for line in report(taken):
        print(line)
    if taken["images"]:
        kept = {key: value for key, value in taken.items() if key != "culprits"}
        into.write_text(json.dumps(kept, indent=CORPUS_INDENT) + "\n")
    failed = any(taken["properties"].values()) or not taken["images"]
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
