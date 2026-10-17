import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402

from sn76489 import tone  # noqa: E402


class PeriodTest(unittest.TestCase):
    def test_a_first_byte_sets_the_four_least_significant_bits(self) -> None:
        # Arrange
        period = 0b1111110000

        # Act
        changed = tone.with_low(period, 0b1010)

        # Assert
        self.assertEqual(changed, 0b1111111010)

    def test_a_second_byte_sets_the_six_most_significant_bits(self) -> None:
        # Arrange
        period = 0b0000000101

        # Act
        changed = tone.with_high(period, 0b101101)

        # Assert
        self.assertEqual(changed, 0b1011010101)

    def test_bits_outside_each_field_are_ignored(self) -> None:
        # Arrange
        period = 0

        # Act
        changed = (tone.with_low(period, 0xF5), tone.with_high(period, 0xFF))

        # Assert
        self.assertEqual(changed, (0b0101, 0b1111110000))


class CounterTest(unittest.TestCase):
    def test_the_counter_decrements_by_one(self) -> None:
        # Arrange
        counter = 2

        # Act
        counted = tone.counted(counter)

        # Assert
        self.assertEqual(counted, 1)

    def test_a_ten_stage_counter_borrows_from_zero_to_1023(self) -> None:
        # Arrange
        counter = 0

        # Act
        counted = tone.counted(counter)

        # Assert
        self.assertEqual(counted, 1023)


if __name__ == "__main__":
    unittest.main()
