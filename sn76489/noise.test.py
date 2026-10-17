import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402

from sn76489 import noise  # noqa: E402

RESET = 0x4000


class ShiftTest(unittest.TestCase):
    def test_a_reset_register_holds_only_its_highest_bit(self) -> None:
        # Arrange
        width = noise.WIDTH

        # Act
        top = noise.TOP

        # Assert
        self.assertEqual((width, top), (15, RESET))

    def test_white_noise_feeds_bits_0_and_1_exclusive_or_into_bit_14(self) -> None:
        # Arrange
        register = 0b000000000000001

        # Act
        shifted = noise.shifted(register, white=True)

        # Assert
        self.assertEqual(shifted, 0b100000000000000)

    def test_equal_taps_feed_back_a_zero(self) -> None:
        # Arrange
        register = 0b000000000000011

        # Act
        shifted = noise.shifted(register, white=True)

        # Assert
        self.assertEqual(shifted, 0b000000000000001)

    def test_periodic_noise_feeds_bit_0_alone(self) -> None:
        # Arrange
        register = 0b000000000000011

        # Act
        shifted = noise.shifted(register, white=False)

        # Assert
        self.assertEqual(shifted, 0b100000000000001)

    def test_periodic_noise_repeats_every_15_shifts(self) -> None:
        # Arrange
        register = RESET

        # Act
        seen = []
        for _ in range(30):
            register = noise.shifted(register, white=False)
            seen.append(register & 1)

        # Assert
        self.assertEqual((seen[:15], seen[15:]), ([0] * 13 + [1, 0], [0] * 13 + [1, 0]))


class ControlTest(unittest.TestCase):
    def test_the_feedback_bit_selects_white_noise(self) -> None:
        # Arrange
        controls = (0b000, 0b100)

        # Act
        white = [noise.is_white(one) for one in controls]

        # Assert
        self.assertEqual(white, [False, True])

    def test_the_three_fixed_rates_are_512_1024_and_2048_input_clocks(self) -> None:
        # Arrange
        prescale = 16

        # Act
        rates = [noise.rate(one) * prescale for one in (0, 1, 2)]

        # Assert
        self.assertEqual(rates, [512, 1024, 2048])

    def test_the_fourth_setting_follows_tone_three(self) -> None:
        # Arrange
        controls = range(8)

        # Act
        following = [one for one in controls if noise.follows_tone_three(one)]

        # Assert
        self.assertEqual(following, [3, 7])


if __name__ == "__main__":
    unittest.main()
