import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import ast  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import unittest  # noqa: E402
from typing import Any  # noqa: E402

from sn76489 import doctor  # noqa: E402

SOURCE = ROOT / "sn76489" / "doctor.py"


def broken(*_: object) -> Any:
    raise ValueError("this build refuses")


class Silent:
    ready = True
    bits = (0, 0, 0, 0)
    shift = 0

    def write(self, _: int) -> None: ...

    def tick(self) -> None: ...

    def clock(self) -> None: ...


class Stuck(Silent):
    ready = False


def one_model() -> Any:
    model = type("Model", (), {"load_clocks": 32})()
    return type("Package", (), {"MODELS": {"sn76489an": model}})()


def folder_with(name: str, text: str) -> Path:
    where = Path(tempfile.mkdtemp()) / name
    where.write_text(text)
    return where


class VersionTest(unittest.TestCase):
    def test_it_reads_the_version_out_of_the_file_beside_it(self) -> None:
        # Arrange
        beside = ROOT / "sn76489" / "version.py"

        # Act
        found = doctor._version(beside)

        # Assert
        self.assertEqual(found, doctor.VERSION)

    def test_a_file_with_no_version_in_it_reads_as_unknown(self) -> None:
        # Arrange
        path = folder_with("version.py", "RELEASE = 1\n")

        # Act
        found = doctor._version(path)

        # Assert
        self.assertEqual(found, "unknown")


class ImportsTest(unittest.TestCase):
    def test_nothing_from_its_own_package_is_imported_at_the_top(self) -> None:
        # Arrange
        tree = ast.parse(SOURCE.read_text())

        # Act
        reached = [
            node.module or ""
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and (node.level or "sn76489" in str(node.module))
        ]

        # Assert
        self.assertEqual(reached, [])


class ReachableTest(unittest.TestCase):
    def test_a_root_that_is_not_on_the_path_is_put_there(self) -> None:
        # Arrange
        path: list[str] = []

        # Act
        added = doctor._reachable(Path("/somewhere"), path)

        # Assert
        self.assertEqual((added, path), (True, ["/somewhere"]))

    def test_a_root_already_on_the_path_is_left_alone(self) -> None:
        # Arrange
        path = ["/somewhere"]

        # Act
        added = doctor._reachable(Path("/somewhere"), path)

        # Assert
        self.assertEqual((added, path), (False, ["/somewhere"]))


class FindingTest(unittest.TestCase):
    def test_a_failing_finding_carries_its_advice(self) -> None:
        # Arrange
        found = doctor.Finding("a name", False, "what was there", "what to do")

        # Act
        shown = found.report

        # Assert
        self.assertEqual(shown, f"{found.line}\n         what to do")

    def test_a_passing_finding_carries_no_advice(self) -> None:
        # Arrange
        found = doctor.Finding("a name", True, "what was there", "what to do")

        # Act
        shown = found.report

        # Assert
        self.assertEqual(shown, "  ok    a name: what was there")

    def test_a_finding_reads_as_what_it_is(self) -> None:
        # Arrange
        found = doctor.Finding("a name", False, "detail")

        # Act
        shown = repr(found)

        # Assert
        self.assertEqual(shown, "<Finding a name not ok>")


class DrivingTest(unittest.TestCase):
    def test_the_package_imports(self) -> None:
        # Arrange
        check = doctor._package

        # Act
        found = check()

        # Assert
        self.assertEqual((found.ok, "sn76489" in found.detail), (True, True))

    def test_every_model_builds(self) -> None:
        # Arrange
        check = doctor._building

        # Act
        found = check()

        # Assert
        self.assertEqual((found.ok, found.detail), (True, "built sn76489an, sn76494n"))

    def test_a_tone_toggles_every_n_periods(self) -> None:
        # Arrange
        check = doctor._toning

        # Act
        found = check()

        # Assert
        self.assertEqual((found.ok, found.detail.endswith("every [5] periods")), (True, True))

    def test_ready_holds_for_each_models_load_time(self) -> None:
        # Arrange
        check = doctor._loading

        # Act
        found = check()

        # Assert
        self.assertEqual(
            (found.ok, found.detail),
            (
                True,
                "sn76489an held READY for 32 clocks, sn76494n held READY for 4 clocks",
            ),
        )

    def test_a_noise_write_clears_the_shift_register(self) -> None:
        # Arrange
        check = doctor._noising

        # Act
        found = check()

        # Assert
        self.assertEqual((found.ok, found.detail.endswith("0x4000")), (True, True))


class RefusingTest(unittest.TestCase):
    def test_a_package_that_will_not_import_is_reported_by_what_it_threw(self) -> None:
        # Arrange
        load = broken

        # Act
        found = doctor._package(load)

        # Assert
        self.assertEqual((found.ok, found.detail), (False, "ValueError: this build refuses"))

    def test_each_driving_check_reports_what_it_threw(self) -> None:
        # Arrange
        checks = (doctor._building, doctor._toning, doctor._loading, doctor._noising)

        # Act
        found = [check(broken) for check in checks]

        # Assert
        self.assertEqual(
            {(one.ok, one.detail) for one in found},
            {(False, "ValueError: this build refuses")},
        )

    def test_a_tone_that_never_toggles_is_reported(self) -> None:
        # Arrange
        silent = lambda _model: Silent()  # noqa: E731

        # Act
        found = doctor._toning(silent)

        # Assert
        self.assertEqual((found.ok, found.detail.endswith("every [] periods")), (False, True))

    def test_ready_that_never_rises_is_reported(self) -> None:
        # Arrange
        stuck = lambda _model: Stuck()  # noqa: E731

        # Act
        found = doctor._loading(one_model, stuck)

        # Assert
        self.assertEqual((found.ok, found.detail), (False, "sn76489an held READY for 33 clocks"))

    def test_a_shift_register_left_at_zero_is_reported(self) -> None:
        # Arrange
        silent = lambda _model: Silent()  # noqa: E731

        # Act
        found = doctor._noising(silent)

        # Assert
        self.assertEqual((found.ok, found.detail.endswith("0x0000")), (False, True))


class DataSheetTest(unittest.TestCase):
    def test_an_absent_data_sheet_is_reported_as_absent_and_not_as_a_fault(self) -> None:
        # Arrange
        nowhere = Path(tempfile.mkdtemp())

        # Act
        found = doctor._data_sheet(held=nowhere)

        # Assert
        self.assertEqual((found.ok, found.detail.startswith("not here")), (True, True))

    def test_a_different_file_in_its_place_is_a_fault(self) -> None:
        # Arrange
        entry = json.loads(doctor.DOCUMENTS.read_text())["documents"][0]
        held = Path(tempfile.mkdtemp())
        (held / entry["file"]).parent.mkdir(parents=True)
        (held / entry["file"]).write_bytes(b"not the scan")

        # Act
        found = doctor._data_sheet(held=held)

        # Assert
        self.assertEqual((found.ok, found.detail.endswith("is a different file")), (False, True))

    def test_a_record_that_will_not_parse_is_reported(self) -> None:
        # Arrange
        manifest = folder_with("documents.json", "{")

        # Act
        found = doctor._data_sheet(manifest=manifest)

        # Assert
        self.assertEqual((found.ok, found.detail.startswith("JSONDecodeError")), (False, True))


class CorpusTest(unittest.TestCase):
    def test_the_corpus_here_names_the_images_behind_it(self) -> None:
        # Arrange
        held = json.loads(doctor.CORPUS.read_text())

        # Act
        found = doctor._corpus()

        # Assert
        self.assertEqual((found.ok, found.detail), (True, f"{held['images']} images behind it"))

    def test_an_absent_corpus_is_a_fault(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp()) / "corpus.json"

        # Act
        found = doctor._corpus(where)

        # Assert
        self.assertEqual((found.ok, found.detail.startswith("not here")), (False, True))

    def test_a_corpus_over_nothing_is_a_fault(self) -> None:
        # Arrange
        where = folder_with("corpus.json", '{"images": 0}')

        # Act
        found = doctor._corpus(where)

        # Assert
        self.assertFalse(found.ok)

    def test_a_corpus_that_will_not_parse_is_reported(self) -> None:
        # Arrange
        where = folder_with("corpus.json", "[]")

        # Act
        found = doctor._corpus(where)

        # Assert
        self.assertEqual((found.ok, found.detail.startswith("TypeError")), (False, True))


class HarnessTest(unittest.TestCase):
    def test_an_absent_board_is_reported_as_absent_and_not_as_a_fault(self) -> None:
        # Arrange
        find = lambda _name: None  # noqa: E731

        # Act
        found = doctor._harness(find)

        # Assert
        self.assertEqual((found.ok, "not checked out" in found.detail), (True, True))

    def test_a_present_board_is_named_where_it_was_found(self) -> None:
        # Arrange
        find = lambda _name: type("Spec", (), {"origin": "/here/tms9918/__init__.py"})()  # noqa: E731

        # Act
        found = doctor._harness(find)

        # Assert
        self.assertEqual(found.detail, "ti-tms9918-python found at /here/tms9918/__init__.py")

    def test_a_lookup_that_throws_is_reported(self) -> None:
        # Arrange
        find = broken

        # Act
        found = doctor._harness(find)

        # Assert
        self.assertFalse(found.ok)

    def test_the_board_is_looked_for_inside_the_submodule_folder(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp())
        (where / "tms9918").mkdir()
        (where / "tms9918" / "__init__.py").write_text("")

        # Act
        found = doctor.look_in(where)("tms9918")

        # Assert
        self.assertEqual(found.origin, str(where / "tms9918" / "__init__.py"))

    def test_and_a_folder_without_it_finds_nothing(self) -> None:
        # Arrange
        where = Path(tempfile.mkdtemp())

        # Act
        found = doctor.look_in(where)("tms9918")

        # Assert
        self.assertIsNone(found)

    def test_the_folder_looked_in_is_the_one_the_census_reads(self) -> None:
        # Arrange
        expected = doctor.ROOT / "ti-tms9918-python"

        # Act
        held = doctor.BOARD

        # Assert
        self.assertEqual(held, expected)


class ReportTest(unittest.TestCase):
    def test_a_clean_run_says_so_and_returns_zero(self) -> None:
        # Arrange
        said: list[str] = []
        examine = lambda: [doctor.Finding("a", True, "fine")]  # noqa: E731

        # Act
        code = doctor.main((), examine, said.append)

        # Assert
        self.assertEqual((code, said[-1]), (0, "  1 checks, nothing to report"))

    def test_a_run_with_a_fault_counts_it_and_returns_one(self) -> None:
        # Arrange
        said: list[str] = []
        examine = [doctor.Finding("a", True, "fine"), doctor.Finding("b", False, "no")].copy

        # Act
        code = doctor.main((), examine, said.append)

        # Assert
        self.assertEqual((code, said[-1]), (1, "  1 of 2 checks did not pass"))

    def test_the_full_examination_covers_every_check_it_names(self) -> None:
        # Arrange
        named = list(doctor.CHECKS)

        # Act
        found = [one.name for one in doctor.examine()]

        # Assert
        self.assertEqual(found, named)


class AsDocumentedTest(unittest.TestCase):
    def test_running_it_as_a_file_prints_a_report_rather_than_a_traceback(self) -> None:
        # Arrange
        elsewhere = tempfile.mkdtemp()

        # Act
        finished = subprocess.run(
            [sys.executable, str(SOURCE)],
            capture_output=True,
            text=True,
            cwd=elsewhere,
            check=False,
        )

        # Assert
        self.assertEqual((finished.returncode, "Traceback" in finished.stderr), (0, False))
        self.assertIn("checks, nothing to report", finished.stdout)

    def test_the_readme_names_the_invocation_that_works(self) -> None:
        # Arrange
        readme = ROOT / "README.md"

        # Act
        said = readme.read_text()

        # Assert
        self.assertIn("python3 sn76489/doctor.py", said)


if __name__ == "__main__":
    unittest.main()
