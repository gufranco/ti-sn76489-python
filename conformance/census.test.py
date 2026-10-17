import contextlib
import io
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from conformance import board, census  # noqa: E402

READY = board.why_not() is None

LD_A = 0x3E

OUT = 0xD3

JR = 0x18

DI = 0xF3

SOUND_PORT = 0x7F


def program(*parts: int) -> bytes:
    image = bytearray(0x2000)
    image[: len(parts)] = bytes(parts)
    return bytes(image)


def sound_write(value: int) -> tuple[int, ...]:
    return (LD_A, value, OUT, SOUND_PORT)


SOUNDS = program(*sound_write(0x9A), *sound_write(0xE5), *sound_write(0x80), DI, JR, 0xFE)

SILENT = program(DI, JR, 0xFE)


def archive(folder: Path, name: str, members: dict[str, bytes]) -> Path:
    where = folder / name
    with zipfile.ZipFile(where, "w") as bundle:
        for member, data in members.items():
            bundle.writestr(member, data)
    return where


def run_main(argv: list[str], into: Path) -> tuple[int, str]:
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        code = census.main(argv, into=into)
    return code, said.getvalue()


def heard(**changes: Any) -> dict[str, Any]:
    found: dict[str, Any] = {
        "first": [1],
        "second": [],
        "noise": [],
        "attenuation": [10],
        "zero": False,
        "early": 0,
        "writes": 1,
        "locked": False,
        "raised": None,
    }
    return {**found, **changes}


class ImagesTest(unittest.TestCase):
    def test_images_inside_an_archive_are_read_with_the_set_they_came_from(
        self,
    ) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        where = archive(folder, "1 Japan.zip", {"a.sg": SOUNDS, "notes.txt": b"x"})

        # Act
        found = list(census.images_in(where))

        # Assert
        self.assertEqual(found, [("1 Japan.zip", "a.sg", SOUNDS)])

    def test_a_directory_is_walked_for_images(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        (folder / "b.sc").write_bytes(SILENT)

        # Act
        found = list(census.images_in(folder))

        # Assert
        self.assertEqual(found, [(folder.name, "b.sc", SILENT)])

    def test_a_lone_image_is_read_as_its_own_set(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        lone = folder / "c.sg"
        lone.write_bytes(SILENT)

        # Act
        found = list(census.images_in(lone))

        # Assert
        self.assertEqual(found, [(folder.name, "c.sg", SILENT)])

    def test_a_directory_opens_its_archives_and_passes_over_other_files(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        archive(folder, "2 Taiwan.zip", {"d.sg": SOUNDS})
        (folder / "readme.txt").write_bytes(b"x")

        # Act
        found = list(census.images_in(folder))

        # Assert
        self.assertEqual(found, [("2 Taiwan.zip", "d.sg", SOUNDS)])

    def test_a_lone_file_that_is_no_image_yields_nothing(self) -> None:
        # Arrange
        lone = Path(tempfile.mkdtemp()) / "notes.txt"
        lone.write_bytes(b"x")

        # Act
        found = list(census.images_in(lone))

        # Assert
        self.assertEqual(found, [])


class GatingTest(unittest.TestCase):
    def test_a_retail_sg_1000_image_is_gated(self) -> None:
        # Arrange
        pairs = [("2 Taiwan.zip", "x.sg"), ("3 Other Regions.zip", "y.sg")]

        # Act
        gated = [census.gated(where, name) for where, name in pairs]

        # Assert
        self.assertEqual(gated, [True, True])

    def test_hacks_homebrew_and_other_machines_only_report(self) -> None:
        # Arrange
        pairs = [
            ("4 Palette Hacks.zip", "x.sg"),
            ("4 Homebrew.zip", "y.sg"),
            ("1 Japan.zip", "[BIOS] z.sg"),
            ("1 Japan.zip", "Choplifter (Japan) (Beta).sg"),
            ("1 Japan.zip", "w.sc"),
        ]

        # Act
        gated = [census.gated(where, name) for where, name in pairs]

        # Assert
        self.assertEqual(gated, [False, False, False, False, False])


@unittest.skipUnless(READY, "ti-tms9918-python is not checked out")
class TakeTest(unittest.TestCase):
    def test_a_census_counts_images_once_by_digest(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        where = archive(folder, "1 Japan.zip", {"a.sg": SOUNDS, "copy.sg": SOUNDS})

        # Act
        taken = census.take([where], frames=2, jobs=1)

        # Assert
        self.assertEqual((taken["listings"], taken["images"], taken["gated"]), (2, 1, 1))

    def test_the_registers_and_values_reached_are_counted_by_image(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        where = archive(folder, "1 Japan.zip", {"a.sg": SOUNDS})

        # Act
        taken = census.take([where], frames=2, jobs=1)

        # Assert
        self.assertEqual(
            (taken["first"], taken["noise"], taken["attenuation"]),
            ({"0": 1, "1": 1, "6": 1}, {"5": 1}, {"10": 1}),
        )

    def test_an_image_that_never_writes_the_part_is_counted_as_silent(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        where = archive(folder, "1 Japan.zip", {"a.sg": SILENT})

        # Act
        taken = census.take([where], frames=2, jobs=1)

        # Assert
        self.assertEqual((taken["silent"], sum(taken["properties"].values())), (1, 0))

    def test_writes_inside_the_load_time_are_counted_by_population(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        where = archive(folder, "4 Homebrew.zip", {"a.sg": SOUNDS})

        # Act
        taken = census.take([where], frames=2, jobs=1)

        # Assert
        self.assertEqual(taken["early"], {"retail": 0, "other": 2})

    def test_workers_give_the_same_answer_as_one_process(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        where = archive(folder, "1 Japan.zip", {"a.sg": SOUNDS, "b.sg": SILENT})

        # Act
        alone, shared = census.take([where], 2, 1), census.take([where], 2, 2)

        # Assert
        self.assertEqual(alone, shared)


class Raising:
    def __init__(self, _rom: bytes) -> None:
        self.frames = 0

    def run_frames(self, _count: int) -> None:
        raise IndexError("planted")


class FaultTest(unittest.TestCase):
    def test_an_image_the_model_raises_on_is_reported_with_what_it_raised(self) -> None:
        # Arrange
        job = (SOUNDS, 2)

        # Act
        found = census.examine(job, Raising)

        # Assert
        self.assertEqual(found["raised"], "IndexError: planted at frame 0")

    def test_and_counted_against_the_property_and_named(self) -> None:
        # Arrange
        images = [(False, SOUNDS, "a.sg")]
        results = [heard(raised="IndexError: planted at frame 0")]

        # Act
        broken = census._tally(images, results)["properties"][census.RAISES_NOTHING]
        named = census._culprits(images, results)[census.RAISES_NOTHING]

        # Assert
        self.assertEqual((broken, named), (1, ["a.sg: IndexError: planted at frame 0"]))

    def test_a_shift_register_found_at_zero_breaks_a_property(self) -> None:
        # Arrange
        images = [(True, SOUNDS, "a.sg")]
        results = [heard(locked=True)]

        # Act
        broken = census._tally(images, results)["properties"][census.NEVER_LOCKS]
        named = census._culprits(images, results)[census.NEVER_LOCKS]

        # Assert
        self.assertEqual((broken, named), (1, ["a.sg"]))


@unittest.skipUnless(READY, "ti-tms9918-python is not checked out")
class MainTest(unittest.TestCase):
    def test_a_census_writes_its_corpus_and_reports_what_it_examined(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        where = archive(folder, "1 Japan.zip", {"a.sg": SOUNDS})
        into = folder / "corpus.json"

        # Act
        code, said = run_main([str(where), "--frames", "2", "--jobs", "1"], into)

        # Assert
        self.assertEqual((code, json.loads(into.read_text())["images"]), (0, 1))
        self.assertIn("1 distinct images", said)

    def test_the_names_behind_an_observation_are_printed_but_not_kept(self) -> None:
        # Arrange
        folder = Path(tempfile.mkdtemp())
        where = archive(folder, "1 Japan.zip", {"busy.sg": SOUNDS})
        into = folder / "corpus.json"

        # Act
        code, said = run_main([str(where), "--frames", "2", "--jobs", "1"], into)

        # Assert
        self.assertEqual((code, "         busy.sg: 2" in said), (0, True))
        self.assertNotIn("culprits", json.loads(into.read_text()))


class ReportTest(unittest.TestCase):
    def test_early_writes_are_reported_by_image_without_failing_anything(self) -> None:
        # Arrange
        images = [(True, SOUNDS, "a.sg")]
        results = [heard(early=3)]
        taken = {
            "listings": 1,
            "images": 1,
            "gated": 1,
            "frames": 2,
            **census._tally(images, results),
            "culprits": census._culprits(images, results),
        }

        # Act
        lines = census.report(taken)

        # Assert
        self.assertEqual(lines[-2:], [f"  observed  {census.EARLY}: 1 images", "         a.sg: 3"])
        self.assertEqual(sum(taken["properties"].values()), 0)


class UsageTest(unittest.TestCase):
    def test_no_path_prints_the_usage(self) -> None:
        # Arrange
        into = Path(tempfile.mkdtemp()) / "corpus.json"

        # Act
        code, said = run_main([], into)

        # Assert
        self.assertEqual((code, "usage" in said), (2, True))

    def test_an_absent_path_is_named_and_examines_nothing(self) -> None:
        # Arrange
        into = Path(tempfile.mkdtemp()) / "corpus.json"

        # Act
        code, said = run_main(["/nonexistent/library"], into)

        # Assert
        self.assertEqual((code, "absent: /nonexistent/library" in said), (1, True))
        self.assertIn("0 distinct images", said)

    def test_a_bad_option_prints_the_usage(self) -> None:
        # Arrange
        into = Path(tempfile.mkdtemp()) / "corpus.json"

        # Act
        code, said = run_main(["x", "--frames"], into)

        # Assert
        self.assertEqual((code, "usage" in said), (2, True))


if __name__ == "__main__":
    unittest.main()
