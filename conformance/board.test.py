import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import board  # noqa: E402

PRESENT = board.why_not() is None

LD_A = 0x3E

OUT_N_A = 0xD3

JR_SELF = (0x18, 0xFE)

SOUND_PORT = 0x7F

VIDEO_PORT = 0xBF

ROM_SIZE = 0x2000


def program(*values: int) -> bytes:
    code = bytearray()
    for value in values:
        code += bytes((LD_A, value, OUT_N_A, SOUND_PORT))
    code += bytes(JR_SELF)
    return bytes(code) + bytes(ROM_SIZE - len(code))


def run(sound: Any, instructions: int) -> None:
    for _ in range(instructions):
        sound.cpu.step()


class AbsenceTest(unittest.TestCase):
    def test_a_missing_board_is_named_with_the_command_that_fetches_it(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp())

        # Act
        said = board.why_not(where)

        # Assert
        self.assertIn("git submodule update --init --recursive", str(said))


@unittest.skipUnless(PRESENT, "ti-tms9918-python is not checked out")
class SoundBoardTest(unittest.TestCase):
    def test_a_write_to_the_sound_port_reaches_the_part(self) -> None:
        # Arrange
        sound = board.SoundBoard(program(0x9A))

        # Act
        run(sound, 2)

        # Assert
        self.assertEqual(sound.part.steps[0], 0x0A)

    def test_a_write_to_the_video_ports_does_not_reach_the_part(self) -> None:
        # Arrange
        code = bytes((LD_A, 0x9A, OUT_N_A, VIDEO_PORT, *JR_SELF))
        sound = board.SoundBoard(code + bytes(ROM_SIZE - len(code)))

        # Act
        run(sound, 2)

        # Assert
        self.assertEqual(sound.heard.writes, 0)

    def test_the_part_ticks_once_per_processor_cycle(self) -> None:
        # Arrange
        sound = board.SoundBoard(program(0x9A))
        before = sound.part.ticks

        # Act
        run(sound, 2)

        # Assert
        self.assertEqual(sound.part.ticks - before, 7 + 11)

    def test_every_write_is_counted_by_the_register_it_reaches(self) -> None:
        # Arrange
        sound = board.SoundBoard(program(0x9A, 0x03, 0xE5))

        # Act
        run(sound, 6)

        # Assert
        self.assertEqual(
            (dict(sound.heard.first), dict(sound.heard.second)), ({1: 1, 6: 1}, {1: 1})
        )

    def test_a_write_inside_the_load_time_of_the_last_is_counted(self) -> None:
        # Arrange
        sound = board.SoundBoard(program(0x9A, 0xBA))

        # Act
        run(sound, 4)

        # Assert
        self.assertEqual(sound.heard.early, 1)

    def test_noise_settings_and_periods_are_noted(self) -> None:
        # Arrange
        sound = board.SoundBoard(program(0xE7, 0x80, 0x00))

        # Act
        run(sound, 6)

        # Assert
        self.assertEqual((set(sound.heard.noise), sound.heard.zero_periods), ({7}, 1))


if __name__ == "__main__":
    unittest.main()
