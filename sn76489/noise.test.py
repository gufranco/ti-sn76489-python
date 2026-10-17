import sys
from itertools import pairwise
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402

import sn76489  # noqa: E402

CLEARED = 0x4000

WHITE_AT_512 = 0xE4

PERIODIC_AT_512 = 0xE0

TONE_THREE = 0xC0

SHIFT_LIMIT = 1 << 20


def written(*values: int) -> Any:
    part = sn76489.Chip("sn76489an", seed=13)
    for value in values:
        part.write(value)
        while not part.ready:
            part.tick()
    return part


def shifts(part: Any, count: int) -> list[tuple[int, int]]:
    found: list[tuple[int, int]] = []
    limit = part.ticks + SHIFT_LIMIT
    while len(found) < count and part.ticks < limit:
        before = part.shift
        part.tick()
        if part.shift != before:
            found.append((part.ticks, part.shift))
    return found


def gaps(found: list[tuple[int, int]]) -> set[int]:
    return {later[0] - earlier[0] for earlier, later in pairwise(found[1:])}


class ShiftTest(unittest.TestCase):
    def test_a_noise_write_leaves_only_the_highest_of_15_bits(self) -> None:
        # Arrange
        part = sn76489.Chip("sn76489an", seed=13)

        # Act
        part.write(WHITE_AT_512)

        # Assert
        self.assertEqual(part.shift, CLEARED)

    def test_white_noise_feeds_bits_0_and_1_exclusive_or_into_bit_14(self) -> None:
        # Arrange
        part = written(WHITE_AT_512)

        # Act
        found = shifts(part, 15)

        # Assert
        self.assertEqual([register for _, register in found[12:]], [0x0002, 0x4001, 0x6000])

    def test_white_noise_outputs_bit_0(self) -> None:
        # Arrange
        part = written(WHITE_AT_512)

        # Act
        found = shifts(part, 16)

        # Assert
        self.assertEqual([register & 1 for _, register in found], [0] * 13 + [1, 0, 0])

    def test_periodic_noise_feeds_bit_0_alone_and_repeats_every_15_shifts(self) -> None:
        # Arrange
        part = written(PERIODIC_AT_512)

        # Act
        found = shifts(part, 30)

        # Assert
        self.assertEqual([register & 1 for _, register in found], ([0] * 13 + [1, 0]) * 2)


class RateTest(unittest.TestCase):
    def test_the_three_fixed_rates_are_512_1024_and_2048_input_clocks(self) -> None:
        # Arrange
        controls = (WHITE_AT_512, WHITE_AT_512 | 1, WHITE_AT_512 | 2)

        # Act
        found = [gaps(shifts(written(control), 4)) for control in controls]

        # Assert
        self.assertEqual(found, [{512}, {1024}, {2048}])

    def test_the_fourth_setting_shifts_once_per_cycle_of_tone_three(self) -> None:
        # Arrange
        part = written(TONE_THREE | 3, 0, WHITE_AT_512 | 3)

        # Act
        found = shifts(part, 5)

        # Assert
        self.assertEqual(gaps(found), {2 * 3 * 16})

    def test_and_does_so_for_periodic_noise_too(self) -> None:
        # Arrange
        part = written(TONE_THREE | 3, 0, PERIODIC_AT_512 | 3)

        # Act
        found = shifts(part, 5)

        # Assert
        self.assertEqual(gaps(found), {2 * 3 * 16})


if __name__ == "__main__":
    unittest.main()
