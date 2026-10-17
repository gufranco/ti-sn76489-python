import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402

import sn76489  # noqa: E402

TONE_ONE_LEVEL = 0x90


def gain_at(step: int) -> float:
    part = sn76489.Chip("sn76489an", seed=5)
    part.write(TONE_ONE_LEVEL | step)
    return float(part.gains[0])


def amplitude(decibels: int) -> float:
    return float(10 ** (-decibels / 20))


class TableOneTest(unittest.TestCase):
    def test_each_single_bit_weighs_what_table_1_prints(self) -> None:
        # Arrange
        steps = (0b0001, 0b0010, 0b0100, 0b1000)

        # Act
        gains = [gain_at(step) for step in steps]

        # Assert
        for found, decibels in zip(gains, (2, 4, 8, 16), strict=True):
            self.assertAlmostEqual(found, amplitude(decibels))

    def test_bits_set_together_add_to_a_28_db_maximum(self) -> None:
        # Arrange
        step = 0b1110

        # Act
        gain = gain_at(step)

        # Assert
        self.assertAlmostEqual(gain, amplitude(28))

    def test_all_four_bits_set_is_off(self) -> None:
        # Arrange
        step = 0b1111

        # Act
        gain = gain_at(step)

        # Assert
        self.assertEqual(gain, 0.0)

    def test_no_attenuation_is_full_gain(self) -> None:
        # Arrange
        step = 0

        # Act
        gain = gain_at(step)

        # Assert
        self.assertEqual(gain, 1.0)

    def test_20_db_is_a_tenth_of_the_amplitude(self) -> None:
        # Arrange
        step = 0b1010

        # Act
        gain = gain_at(step)

        # Assert
        self.assertAlmostEqual(gain, 0.1)


if __name__ == "__main__":
    unittest.main()
