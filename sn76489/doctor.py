from __future__ import annotations

import hashlib
import importlib.machinery
import json
import platform
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, override

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable, Sequence


def installed_version(where: Path | None = None) -> str:
    found = re.search(
        r"""VERSION\s*[:=][^"']*["']([^"']+)["']""",
        (where or Path(__file__).resolve().parent / "version.py").read_text(),
    )
    return found.group(1) if found else "unknown"


VERSION = installed_version()

ROOT = Path(__file__).resolve().parent.parent


def reachable(root: Path = ROOT, path: list[str] | None = None) -> bool:
    where = sys.path if path is None else path
    if str(root) in where:
        return False
    where.insert(0, str(root))
    return True


reachable()

CORPUS = ROOT / "conformance" / "corpus.json"

DOCUMENTS = ROOT / "conformance" / "documents.json"

HELD_DOCUMENTS = ROOT / "docs"

HARNESS_MODULE = "tms9918"

BOARD = ROOT / "ti-tms9918-python"


def look_in(where: Path) -> Callable[[str], Any]:
    return lambda name: importlib.machinery.PathFinder.find_spec(name, [str(where)])


IN_SUBMODULE = look_in(BOARD)


OLDEST_PYTHON = (3, 12)

TONE_PERIOD = 5

TOGGLES = 4

LIMIT = 2 * 1024 + TONE_PERIOD * (TOGGLES + 1)

CHECKS = (
    "python",
    "package",
    "building",
    "toning",
    "loading",
    "noising",
    "data sheet",
    "corpus",
    "harness",
    "library",
)


class Finding:
    __slots__ = ("advice", "detail", "name", "ok")

    def __init__(self, name: str, ok: bool, detail: str, advice: str | None = None) -> None:
        self.name = name
        self.ok = ok
        self.detail = detail
        self.advice = advice

    @property
    def line(self) -> str:
        return f"  {'ok  ' if self.ok else '   !'}  {self.name}: {self.detail}"

    @property
    def report(self) -> str:
        if self.ok or not self.advice:
            return self.line
        return f"{self.line}\n         {self.advice}"

    @override
    def __repr__(self) -> str:
        return f"<Finding {self.name} {'ok' if self.ok else 'not ok'}>"


def _threw(name: str, error: BaseException, advice: str | None = None) -> Finding:
    return Finding(name, False, f"{type(error).__name__}: {error}", advice)


def check_python() -> Finding:
    running = sys.version_info[:2]
    return Finding(
        "python",
        running >= OLDEST_PYTHON,
        f"{platform.python_version()}",
        f"this package needs {OLDEST_PYTHON[0]}.{OLDEST_PYTHON[1]} or newer",
    )


def _load() -> Any:
    import sn76489

    return sn76489


def check_package(load: Callable[[], Any] = _load) -> Finding:
    try:
        loaded = load()
    except Exception as error:
        return _threw("package", error, "the package did not import from this directory")
    return Finding("package", True, f"sn76489 {loaded.__version__} imported from {ROOT}")


def _settled(part: Any) -> Any:
    while not part.ready:
        part.tick()
    return part


def _ready(model: str) -> Any:
    import sn76489

    return _settled(sn76489.Chip(model))


def _write(part: Any, *values: int) -> None:
    for value in values:
        part.write(value)
        _settled(part)


def check_building(load: Callable[[], Any] = _load) -> Finding:
    try:
        names = sorted(load().MODELS)
        built = [_ready(name).model for name in names]
    except Exception as error:
        return _threw("building", error)
    return Finding(
        "building",
        built == names and bool(names),
        f"built {', '.join(built)}",
        "a model in the catalogue did not build as itself",
    )


def check_toning(ready: Callable[[str], Any] = _ready) -> Finding:
    try:
        part = ready("sn76489an")
        _write(part, 0x80 | TONE_PERIOD, 0x00)
        gaps = _toggles(part)
    except Exception as error:
        return _threw("toning", error)
    return Finding(
        "toning",
        gaps == [TONE_PERIOD] * TOGGLES,
        f"tone 1 at period {TONE_PERIOD} toggled every {sorted(set(gaps))} periods",
        "a tone did not toggle every n periods, so it is not at N/32n",
    )


def _toggles(part: Any) -> list[int]:
    gaps: list[int] = []
    last = part.bits[0]
    since: int | None = None
    for _ in range(LIMIT):
        if len(gaps) == TOGGLES:
            break
        part.clock()
        since = None if since is None else since + 1
        if part.bits[0] == last:
            continue
        last = part.bits[0]
        if since is not None:
            gaps.append(since)
        since = 0
    return gaps


def check_loading(load: Callable[[], Any] = _load, ready: Callable[[str], Any] = _ready) -> Finding:
    try:
        held = {}
        for name, model in sorted(load().MODELS.items()):
            part = ready(name)
            part.write(0x9F)
            waited = 0
            while not part.ready and waited <= model.load_clocks:
                part.tick()
                waited += 1
            held[name] = (waited, model.load_clocks)
    except Exception as error:
        return _threw("loading", error)
    return Finding(
        "loading",
        all(waited == wanted for waited, wanted in held.values()) and bool(held),
        ", ".join(f"{name} held READY for {waited} clocks" for name, (waited, _) in held.items()),
        "READY did not hold for the load time the data sheet prints",
    )


def check_noising(ready: Callable[[str], Any] = _ready) -> Finding:
    try:
        part = ready("sn76489an")
        _write(part, 0xE4)
        cleared = part.shift
    except Exception as error:
        return _threw("noising", error)
    return Finding(
        "noising",
        cleared == 1 << 14,
        f"a noise write left the shift register at {cleared:#06x}",
        "a noise write did not clear the shift register to its top bit",
    )


def check_data_sheet(manifest: Path = DOCUMENTS, held: Path = HELD_DOCUMENTS) -> Finding:
    try:
        entry = json.loads(manifest.read_text())["documents"][0]
        where = held / str(entry["file"])
        if not where.is_file():
            return Finding(
                "data sheet",
                True,
                f"not here: {where}; the quote check will report checking none",
                None,
            )
        agrees = hashlib.sha256(where.read_bytes()).hexdigest() == entry["sha256"]
    except Exception as error:
        return _threw("data sheet", error)
    return Finding(
        "data sheet",
        agrees,
        f"{where.name} is the pinned scan" if agrees else f"{where.name} is a different file",
        "put your own copy in docs/manufacturer/,"
        " then run python3 -m conformance.documents --check",
    )


def check_corpus(path: Path | str = CORPUS) -> Finding:
    where = Path(path)
    if not where.is_file():
        return Finding("corpus", False, f"not here: {where}", "run the census to build one")
    try:
        held = json.loads(where.read_text())
        examined = int(held["images"])
    except Exception as error:
        return _threw("corpus", error, f"{where} did not parse")
    return Finding(
        "corpus",
        examined > 0,
        f"{examined} images behind it",
        "a census that examined no image writes an empty corpus, so check what it walked",
    )


def check_harness(find: Callable[[str], Any] = IN_SUBMODULE) -> Finding:
    try:
        found = find(HARNESS_MODULE)
    except Exception as error:
        return _threw("harness", error)
    if found is None:
        return Finding(
            "harness",
            True,
            "ti-tms9918-python is not checked out; only the census needs it, so the "
            "package and the suite run without it",
        )
    return Finding("harness", True, f"ti-tms9918-python found at {found.origin}")


def check_library() -> Finding:
    return Finding(
        "library",
        True,
        "the census takes the library to walk as an argument,"
        " so there is nothing to be set wrongly",
    )


def examine(corpus: Path | str = CORPUS) -> list[Finding]:
    return [
        check_python(),
        check_package(),
        check_building(),
        check_toning(),
        check_loading(),
        check_noising(),
        check_data_sheet(),
        check_corpus(corpus),
        check_harness(),
        check_library(),
    ]


def report(found: Sequence[Finding]) -> list[str]:
    from sn76489 import environment

    unwell = [one for one in found if not one.ok]
    lines = [
        f"sn76489 {VERSION} on {platform.python_version()}, {platform.system()}",
        "",
    ]
    lines.append("  the machine")
    lines.extend(environment.lines(ROOT))
    lines.append("")
    lines.append("  this package")
    lines.extend(one.report for one in found)
    lines.append("")
    if unwell:
        lines.append(f"  {len(unwell)} of {len(found)} checks did not pass")
    else:
        lines.append(f"  {len(found)} checks, nothing to report")
    return lines


def main(
    argv: Sequence[str] = (),
    examine: Callable[..., list[Finding]] = examine,
    say: Callable[[str], None] = print,
) -> int:
    found = examine()
    for line in report(found):
        say(line)
    return 1 if any(not one.ok for one in found) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
