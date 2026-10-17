import statistics
import sys
import time
from collections.abc import Sequence

import sn76489
from sn76489.core import Chip

MEASURED_HERE = 10_700_000

HEADROOM = 10

FLOOR_STEP = 10_000

FLOOR = MEASURED_HERE // HEADROOM // FLOOR_STEP * FLOOR_STEP

TICKS = 3_579_545 // 60

REPEATS = 5

BUSY = (0x8E, 0x0F, 0x90, 0xAF, 0x07, 0xB0, 0xCF, 0x03, 0xD0, 0xE7, 0xF0)

SEED = 76489


def busy_chip() -> Chip:
    part: Chip = sn76489.Chip("sn76489an", seed=SEED)
    for value in BUSY:
        part.write(value)
        while not part.ready:
            part.tick()
    return part


class Timed:
    __slots__ = ("calls", "seconds", "what")

    def __init__(self, what: str, calls: int, seconds: Sequence[float]) -> None:
        self.what = what
        self.calls = calls
        self.seconds = list(seconds)

    def median(self) -> float:
        return statistics.median(self.seconds)

    def rate(self) -> float:
        taken = self.median()
        return self.calls / taken if taken > 0 else 0.0

    def beats(self, floor: int) -> bool:
        return self.rate() >= floor


def measure(calls: int = TICKS, repeats: int = REPEATS) -> Timed:
    seconds = []
    for _ in range(repeats):
        part = busy_chip()
        started = time.perf_counter()
        for _ in range(calls):
            part.tick()
        seconds.append(time.perf_counter() - started)
    return Timed("input clocks with three tones and white noise running", calls, seconds)


def lines_for(found: Timed, floor: int = FLOOR) -> list[str]:
    runtime = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    lines = [
        f"  {found.what}: {found.rate():,.0f} per second"
        f" (median of {len(found.seconds)}) on Python {runtime}",
        f"  floor: {floor:,} per second",
    ]
    if not found.beats(floor):
        lines.append(f"  below the floor: {found.rate():,.0f} is under {floor:,}")
    return lines


def main(calls: int = TICKS, repeats: int = REPEATS, floor: int = FLOOR) -> int:
    found = measure(calls, repeats)
    for line in lines_for(found, floor):
        print(line)
    return 0 if found.beats(floor) else 1


if __name__ == "__main__":
    raise SystemExit(main())
