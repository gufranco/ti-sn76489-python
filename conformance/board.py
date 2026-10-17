import collections
import functools
import importlib
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import sn76489
from sn76489 import core

ROOT = Path(__file__).resolve().parent.parent

BOARD = ROOT / "ti-tms9918-python"

ALIAS = "tms9918_conformance"

OURS = "conformance"

MODEL = "sn76489an"

SEED = 0x7648


def why_not(where: Path = BOARD) -> str | None:
    if (where / "conformance" / "harness.py").is_file():
        return None
    return (
        f"the census runs software on ti-tms9918-python's SG-1000 board from {where}, which"
        " is not checked out. Run git submodule update --init --recursive"
    )


def _named(prefix: str) -> list[str]:
    return [name for name in sys.modules if name.split(".")[0] == prefix]


def _first_then_last(paths: list[str]) -> None:
    for path in paths:
        while path in sys.path:
            sys.path.remove(path)
        sys.path.append(path)


@functools.cache
def borrowed(where: Path = BOARD) -> ModuleType:
    paths = [str(where), str(where / "zilog-z80-python")]
    sys.path[:0] = paths
    ours = {name: sys.modules.pop(name) for name in _named(OURS)}
    try:
        harness = importlib.import_module(f"{OURS}.harness")
        theirs = {name: sys.modules.pop(name) for name in _named(OURS)}
    finally:
        sys.modules.update(ours)
        _first_then_last(paths)
    sys.modules.update({name.replace(OURS, ALIAS, 1): module for name, module in theirs.items()})
    return harness


class Heard:
    __slots__ = (
        "attenuation",
        "early",
        "first",
        "noise",
        "second",
        "writes",
        "zero_periods",
    )

    def __init__(self) -> None:
        self.first: collections.Counter[int] = collections.Counter()
        self.second: collections.Counter[int] = collections.Counter()
        self.noise: collections.Counter[int] = collections.Counter()
        self.attenuation: collections.Counter[int] = collections.Counter()
        self.writes = 0
        self.early = 0
        self.zero_periods = 0

    def note(self, part: core.Chip, value: int, ready: bool) -> None:
        self.writes += 1
        self.early += not ready
        register = part.latched
        (self.first if value & core.LATCH else self.second)[register] += 1
        if register == core.NOISE_REGISTER:
            self.noise[part.control] += 1
        elif register & 1:
            self.attenuation[part.steps[register >> 1]] += 1
        elif part.periods[register >> 1] == 0:
            self.zero_periods += 1


@functools.cache
def sound_board(harness: ModuleType) -> type[Any]:
    class Sound(harness.Board):  # type: ignore[name-defined,misc]
        __slots__ = ("heard", "part")

        def __init__(self, rom: bytes) -> None:
            self.part = sn76489.Chip(MODEL, seed=SEED)
            self.heard = Heard()
            super().__init__(rom)

        def write_port(self, address: int, value: int) -> None:
            if address & harness.PORT_SELECT == harness.SOUND_PORTS:
                ready = self.part.ready
                self.part.write(value)
                self.heard.note(self.part, value, ready)
            super().write_port(address, value)

        def cycle(self) -> None:
            self.part.tick()
            super().cycle()

    return Sound


def SoundBoard(rom: bytes) -> Any:  # noqa: N802
    return sound_board(borrowed())(rom)
