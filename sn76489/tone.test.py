import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402

import sn76489  # noqa: E402

TONE_ONE = 0x80

EDGE_LIMIT = 1 << 18


def written(*values: int) -> Any:
    part = sn76489.Chip("sn76489an", seed=11)
    for value in values:
        part.write(value)
        while not part.ready:
            part.tick()
    return part


def toggles(part: Any, count: int) -> list[int]:
    found: list[int] = []
    limit = part.ticks + EDGE_LIMIT
    while len(found) < count and part.ticks < limit:
        before = part.bits[0]
        part.tick()
        if part.bits[0] != before:
            found.append(part.ticks)
    return found


class PeriodTest(unittest.TestCase):
    def test_a_first_byte_sets_the_four_least_significant_bits(self) -> None:
        # Arrange
        part = written(TONE_ONE, 0b111111)

        # Act
        part.write(TONE_ONE | 0b1010)

        # Assert
        self.assertEqual(part.periods[0], 0b1111111010)

    def test_a_second_byte_sets_the_six_most_significant_bits(self) -> None:
        # Arrange
        part = written(TONE_ONE | 0b0101)

        # Act
        part.write(0b101101)

        # Assert
        self.assertEqual(part.periods[0], 0b1011010101)

    def test_bits_outside_the_second_bytes_field_are_ignored(self) -> None:
        # Arrange
        part = written(TONE_ONE)

        # Act
        part.write(0x7F)

        # Assert
        self.assertEqual(part.periods[0], 0b1111110000)


class CounterTest(unittest.TestCase):
    def test_the_counter_counts_a_period_of_two_down_in_two_periods(self) -> None:
        # Arrange
        part = written(TONE_ONE | 0b0010, 0)

        # Act
        found = toggles(part, 3)

        # Assert
        self.assertEqual([found[1] - found[0], found[2] - found[1]], [32, 32])

    def test_a_period_of_zero_borrows_through_all_1024_counts(self) -> None:
        # Arrange
        part = written(TONE_ONE, 0)

        # Act
        found = toggles(part, 3)

        # Assert
        self.assertEqual([found[1] - found[0], found[2] - found[1]], [1024 * 16, 1024 * 16])


if __name__ == "__main__":
    unittest.main()
