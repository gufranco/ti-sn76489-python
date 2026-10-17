import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402

import sn76489  # noqa: E402
from sn76489.core import Chip  # noqa: E402

TONE_ONE_PERIOD = 0x80

TONE_ONE_LEVEL = 0x90

TONE_THREE_PERIOD = 0xC0

NOISE_CONTROL = 0xE0

NOISE_LEVEL = 0xF0


def loaded(model: str = "sn76489an") -> Chip:
    part: Chip = sn76489.Chip(model, seed=7)
    for _ in range(part.part.load_clocks):
        part.tick()
    return part


def write(part: Chip, *values: int) -> None:
    for value in values:
        part.write(value)
        for _ in range(part.part.load_clocks):
            part.tick()


def set_period(part: Chip, first: int, period: int) -> None:
    write(part, first | (period & 0x0F), (period >> 4) & 0x3F)


def toggle_gaps(part: Chip, channel: int, periods: int) -> list[int]:
    gaps: list[int] = []
    last = part.bits[channel]
    since = 0
    for _ in range(periods):
        part.clock()
        since += 1
        if part.bits[channel] != last:
            last = part.bits[channel]
            gaps.append(since)
            since = 0
    return gaps[1:]


class ClockTest(unittest.TestCase):
    def test_one_period_is_16_input_clocks_on_the_sn76489an(self) -> None:
        # Arrange
        part = loaded()
        before = part.ticks

        # Act
        part.clock()

        # Assert
        self.assertEqual(part.ticks - before, 16)

    def test_and_2_on_the_sn76494n(self) -> None:
        # Arrange
        part = loaded("sn76494n")
        before = part.ticks

        # Act
        part.clock()

        # Assert
        self.assertEqual(part.ticks - before, 2)


class ToneTest(unittest.TestCase):
    def test_a_tone_toggles_every_n_periods_so_a_cycle_is_32n_clocks(self) -> None:
        # Arrange
        part = loaded()
        set_period(part, TONE_ONE_PERIOD, 5)

        # Act
        gaps = toggle_gaps(part, 0, 1100)

        # Assert
        self.assertEqual(set(gaps[1:]), {5})

    def test_a_zero_period_lets_the_ten_stage_counter_run_1024_periods(self) -> None:
        # Arrange
        part = loaded()
        set_period(part, TONE_ONE_PERIOD, 0)

        # Act
        gaps = toggle_gaps(part, 0, 4200)

        # Assert
        self.assertEqual(set(gaps[1:]), {1024})

    def test_a_second_byte_alone_rewrites_the_latched_registers_high_bits(self) -> None:
        # Arrange
        part = loaded()
        set_period(part, TONE_ONE_PERIOD, 0x3A5)

        # Act
        write(part, 0x01)

        # Assert
        self.assertEqual(part.periods[0], 0x015)

    def test_a_first_byte_changes_only_the_low_bits(self) -> None:
        # Arrange
        part = loaded()
        set_period(part, TONE_ONE_PERIOD, 0x3A5)

        # Act
        write(part, TONE_ONE_PERIOD | 0x0C)

        # Assert
        self.assertEqual(part.periods[0], 0x3AC)


class ReadyTest(unittest.TestCase):
    def test_ready_falls_on_a_write_and_rises_32_clocks_later(self) -> None:
        # Arrange
        part = loaded()
        part.write(TONE_ONE_LEVEL)
        seen = [part.ready]

        # Act
        for _ in range(32):
            part.tick()
            seen.append(part.ready)

        # Assert
        self.assertEqual((seen.count(False), seen[-1]), (32, True))

    def test_four_clocks_on_the_sn76494n(self) -> None:
        # Arrange
        part = loaded("sn76494n")
        part.write(TONE_ONE_LEVEL)

        # Act
        held = 0
        while not part.ready:
            part.tick()
            held += 1

        # Assert
        self.assertEqual(held, 4)

    def test_a_write_while_loading_starts_the_count_again(self) -> None:
        # Arrange
        part = loaded()
        part.write(TONE_ONE_LEVEL)
        for _ in range(10):
            part.tick()

        # Act
        part.write(TONE_ONE_LEVEL)

        # Assert
        self.assertEqual(part.loading, 32)


class NoiseTest(unittest.TestCase):
    def test_a_noise_write_clears_the_shift_register_to_its_top_bit(self) -> None:
        # Arrange
        part = loaded()

        # Act
        write(part, NOISE_CONTROL | 0x04)

        # Assert
        self.assertEqual(part.shift, 0x4000)

    def test_a_second_byte_to_the_noise_register_also_clears_it(self) -> None:
        # Arrange
        part = loaded()
        write(part, NOISE_CONTROL | 0x04)
        for _ in range(100):
            part.clock()

        # Act
        write(part, 0x05)

        # Assert
        self.assertEqual((part.control, part.shift), (0x05, 0x4000))

    def test_the_slowest_fixed_rate_shifts_once_every_128_periods(self) -> None:
        # Arrange
        part = loaded()
        write(part, NOISE_CONTROL | 0x02)
        shifts = 0

        # Act
        for _ in range(128 * 10):
            before = part.shift
            part.clock()
            shifts += part.shift != before

        # Assert
        self.assertEqual(shifts, 10)

    def test_following_tone_three_shifts_once_per_tone_three_cycle(self) -> None:
        # Arrange
        part = loaded()
        set_period(part, TONE_THREE_PERIOD, 3)
        write(part, NOISE_CONTROL | 0x03)
        for _ in range(1024):
            part.clock()
        shifts = 0

        # Act
        for _ in range(6 * 50):
            before = part.shift
            part.clock()
            shifts += part.shift != before

        # Assert
        self.assertIn(shifts, (49, 50))


class LevelTest(unittest.TestCase):
    def test_an_attenuation_byte_sets_its_channels_step(self) -> None:
        # Arrange
        part = loaded()

        # Act
        write(part, NOISE_LEVEL | 0x0A)

        # Assert
        self.assertEqual(part.steps[3], 0x0A)

    def test_a_second_byte_to_an_attenuation_register_sets_the_step(self) -> None:
        # Arrange
        part = loaded()
        write(part, TONE_ONE_LEVEL | 0x0F)

        # Act
        write(part, 0x03)

        # Assert
        self.assertEqual(part.steps[0], 0x03)

    def test_the_mix_is_the_gain_of_every_channel_whose_bit_is_high(self) -> None:
        # Arrange
        part = loaded()
        write(part, TONE_ONE_LEVEL, 0xB0 | 0x0F, 0xD0 | 0x0F, NOISE_LEVEL | 0x0F)

        # Act
        mixed = part.level

        # Assert
        self.assertEqual(mixed, 1.0 if part.bits[0] else 0.0)


class ResetTest(unittest.TestCase):
    def test_a_reset_hands_the_part_back(self) -> None:
        # Arrange
        part = loaded()

        # Act
        handed = part.reset()

        # Assert
        self.assertIs(handed, part)

    def test_and_changes_nothing_because_the_part_has_no_reset_pin(self) -> None:
        # Arrange
        part = loaded()
        before = (part.periods[:], part.steps[:], part.shift, part.latched, part.ticks)

        # Act
        part.reset()

        # Assert
        self.assertEqual((part.periods, part.steps, part.shift, part.latched, part.ticks), before)


if __name__ == "__main__":
    unittest.main()
