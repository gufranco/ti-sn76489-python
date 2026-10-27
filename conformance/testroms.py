import hashlib
import json
import os
import sys
import zipfile
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import Any

from conformance import board

RECORD = Path(__file__).resolve().parent / "testroms.json"

PLACES = "TEST_CARTRIDGES"

KEPT = Path(__file__).resolve().parent.parent / "external"

COLUMNS = 32

ROWS = 24

NAME_TABLE_STEP = 0x400

NAME_TABLE_BITS = 0x0F

STAGE = "CHANNEL"

NOTHING_TO_RUN = 2

USAGE_ERROR = 3

INDENT = 2

USAGE = "usage: python3 -m conformance.testroms [--write] [image, folder or zip ...]"


def record(where: Path | str | None = None) -> dict[str, Any]:
    held = json.loads(Path(where or RECORD).read_text())
    assert isinstance(held, dict), "the record does not hold an object"
    return held


def entry(name: str, where: Path | str | None = None) -> dict[str, Any]:
    found = [one for one in record(where)["cartridges"] if one["id"] == name]
    assert found, f"{name} is not in the record"
    return dict(found[0])


def candidates(place: Path) -> Iterator[bytes]:
    if place.is_dir():
        for path in sorted(place.rglob("*")):
            yield from candidates(path)
    elif zipfile.is_zipfile(place):
        with zipfile.ZipFile(place) as archive:
            for member in archive.namelist():
                yield archive.read(member)
    elif place.is_file():
        yield place.read_bytes()


def images(places: Sequence[Path], wanted: set[str]) -> dict[str, bytes]:
    found: dict[str, bytes] = {}
    for place in places:
        for data in candidates(place):
            digest = hashlib.sha256(data).hexdigest()
            if digest in wanted:
                found[digest] = data
    return found


def screen(running: Any) -> list[str]:
    video = running.vdp
    base = (video.registers[2] & NAME_TABLE_BITS) * NAME_TABLE_STEP
    return [
        "".join(chr(video.memory.read8(base + row * COLUMNS + column)) for column in range(COLUMNS))
        for row in range(ROWS)
    ]


def reported(row: str) -> bool:
    text = row.strip()
    printable = all(" " <= character <= "~" for character in row)
    return printable and any(character.isalpha() for character in text) and len(set(text)) > 1


def state(part: Any) -> dict[str, Any]:
    return {"steps": list(part.steps), "periods": list(part.periods), "control": part.control}


def heard(image: bytes, frames: int, every: int) -> dict[str, Any]:
    running = board.SoundBoard(image)
    seen: list[str] = []
    channels: dict[str, Any] = {}
    for _ in range(frames // every):
        running.run_frames(every)
        shown = [row.strip() for row in screen(running) if reported(row)]
        seen = list(dict.fromkeys([*seen, *shown]))
        staged = {row: state(running.part) for row in shown if row.startswith(STAGE)}
        channels = {**channels, **staged}
    return {
        "verdict": seen,
        "channels": channels,
        "writes": running.heard.writes,
        "final": state(running.part),
    }


def options(argv: Sequence[str]) -> tuple[bool, list[Path]] | None:
    write = "--write" in argv
    rest = [one for one in argv if one != "--write"]
    if any(one.startswith("--") for one in rest):
        return None
    return write, [Path(one) for one in rest]


def places_from(given: list[Path], kept: Path) -> list[Path]:
    if given:
        return given
    named = os.environ.get(PLACES, "")
    return [Path(one) for one in named.split(os.pathsep) if one] or [kept]


def judged(one: dict[str, Any], found: dict[str, Any]) -> bool:
    same = all(found[key] == one.get(key) for key in found)
    print(f"{'ran' if same else 'DIFFERS'} {one['id']}: {len(found['verdict'])} lines")
    for line in found["verdict"]:
        print(f"  {line}")
    for row, held in found["channels"].items():
        print(f"  {row}: {json.dumps(held, sort_keys=True)}")
    print(f"  {found['writes']} writes, left at {json.dumps(found['final'], sort_keys=True)}")
    return same


def main(argv: Sequence[str], where: Path | str | None = None, kept: Path = KEPT) -> int:
    parsed = options(argv)
    if parsed is None:
        print(USAGE)
        return USAGE_ERROR
    write, given = parsed
    held = record(where)
    wanted = [one for one in held["cartridges"] if one["outcome"] == "run"]
    found = images(places_from(given, kept), {one["sha256"] for one in wanted})
    if not found:
        print(f"SKIPPED none of the {len(wanted)} pinned images is on this machine")
        return NOTHING_TO_RUN
    good = True
    for one in wanted:
        if one["sha256"] not in found:
            print(f"SKIPPED {one['id']}: not on this machine")
            continue
        measured = heard(found[one["sha256"]], one["frames"], one["every"])
        good = judged(one, measured) and good
        one.update(measured)
    if write:
        Path(where or RECORD).write_text(json.dumps(held, indent=INDENT) + "\n")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
