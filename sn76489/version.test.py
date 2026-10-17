import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402

import sn76489  # noqa: E402
from sn76489 import version  # noqa: E402


class VersionTest(unittest.TestCase):
    def test_the_version_is_three_numbers(self) -> None:
        # Arrange
        held = version.VERSION

        # Act
        parts = held.split(".")

        # Assert
        self.assertEqual(len(parts), 3)
        self.assertTrue(all(part.isdigit() for part in parts))

    def test_the_package_reports_the_same_version(self) -> None:
        # Arrange
        held = version.VERSION

        # Act
        reported = sn76489.__version__

        # Assert
        self.assertEqual(reported, held)


class SurfaceTest(unittest.TestCase):
    def test_everything_it_declares_is_reachable(self) -> None:
        # Arrange
        declared = sn76489.__all__

        # Act
        missing = [name for name in declared if not hasattr(sn76489, name)]

        # Assert
        self.assertEqual(missing, [])


class ReleaseWiringTest(unittest.TestCase):
    def test_the_release_job_rewrites_the_file_the_package_reads(self) -> None:
        # Arrange
        wanted = "sn76489/version.py"

        # Act
        assets = (ROOT / ".releaserc.json").read_text()

        # Assert
        self.assertIn(wanted, assets)

    def test_the_release_job_commits_the_citation_it_stamps(self) -> None:
        # Arrange
        wanted = "CITATION.cff"

        # Act
        assets = (ROOT / ".releaserc.json").read_text()

        # Assert
        self.assertIn(wanted, assets)

    def test_the_script_that_rewrites_it_points_at_the_same_file(self) -> None:
        # Arrange
        wanted = "sn76489/version.py"

        # Act
        script = (ROOT / "scripts" / "set-version.sh").read_text()

        # Assert
        self.assertIn(wanted, script)

    def test_the_script_also_stamps_the_citation(self) -> None:
        # Arrange
        wanted = "CITATION.cff"

        # Act
        script = (ROOT / "scripts" / "set-version.sh").read_text()

        # Assert
        self.assertIn(wanted, script)

    def test_the_citation_carries_the_version_the_package_reports(self) -> None:
        # Arrange
        citation = (ROOT / "CITATION.cff").read_text()

        # Act
        cited = [
            line.removeprefix("version: ").strip()
            for line in citation.splitlines()
            if line.startswith("version: ")
        ]

        # Assert
        self.assertEqual(cited, [version.VERSION])


if __name__ == "__main__":
    unittest.main()
