import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import sn76489  # noqa: E402
from conformance import census, corpus, quotes  # noqa: E402

HELD: dict[str, Any] = json.loads((ROOT / "conformance" / "corpus.json").read_text())


READMES = sorted(ROOT.glob("README*.md"))

BOLD = re.compile(r"\*\*(\d[\d,]*)%?\*\*")

HEADLINE_FIGURES = 5


def headline(text: str) -> list[str]:
    line = next(one for one in text.splitlines() if BOLD.search(one))
    return BOLD.findall(line)[:HEADLINE_FIGURES]


def advertised(held: dict[str, Any]) -> list[str]:
    return [
        str(held["images"]),
        str(held["frames"]),
        str(sum(held["properties"].values())),
        str(len(quotes.collected())),
        str(len(sn76489.MODELS)),
    ]


def table_rows(text: str, images: int) -> list[str]:
    lines = text.splitlines()
    start = next(
        index for index, line in enumerate(lines) if line.startswith("|") and str(images) in line
    )
    rows = []
    for line in lines[start + 2 :]:
        if not line.startswith("|"):
            break
        rows.append(line.split("|")[2].strip())
    return rows


def cells(counts: dict[str, int], keys: tuple[int, ...]) -> str:
    return ", ".join(str(counts.get(str(key), 0)) for key in keys)


def counted_rows(held: dict[str, Any]) -> list[str]:
    first, second, noise = held["first"], held["second"], held["noise"]
    return [
        str(held["silent"]),
        cells(first, (0, 2, 4)),
        cells(first, (1, 3, 5, 7)),
        cells(first, (6,)),
        cells(second, (0, 2, 4)),
        cells(second, (1, 3, 7)),
        cells(second, (6,)),
        cells(noise, (0, 3, 4, 5, 6, 7)),
        str(noise.get("1", 0) + noise.get("2", 0)),
        cells(held["attenuation"], (15,)),
        str(held["zeroPeriods"]),
    ]


def totals(held: dict[str, Any]) -> list[str]:
    early = held["early"]
    return [f"{held['writes']:,}", f"{early['retail']:,}", f"{early['other']:,}"]


def sound() -> dict[str, Any]:
    return {
        "listings": 3,
        "images": 2,
        "gated": 1,
        "frames": 600,
        "properties": dict.fromkeys(census.PROPERTIES, 0),
        "first": {"0": 2, "6": 1},
        "second": {"0": 1},
        "noise": {"4": 1},
        "attenuation": {"15": 2},
        "zeroPeriods": 1,
        "writes": 40,
        "early": {"retail": 0, "other": 0},
        "silent": 0,
    }


def run_main(held: dict[str, Any]) -> tuple[int, str]:
    where = Path(tempfile.mkdtemp()) / "corpus.json"
    where.write_text(json.dumps(held))
    said = io.StringIO()
    with contextlib.redirect_stdout(said):
        code = corpus.main(where)
    return code, said.getvalue()


class ReplayTest(unittest.TestCase):
    def test_the_corpus_here_breaks_no_property(self) -> None:
        # Arrange
        held = HELD

        # Act
        broken = corpus.broken(held)

        # Assert
        self.assertEqual(broken, [])

    def test_and_holds_together(self) -> None:
        # Arrange
        held = HELD

        # Act
        problems = corpus.inconsistent(held)

        # Assert
        self.assertEqual(problems, [])

    def test_and_names_every_property_the_census_gates_on(self) -> None:
        # Arrange
        gated = list(census.PROPERTIES)

        # Act
        named = list(HELD["properties"])

        # Assert
        self.assertEqual(named, gated)

    def test_and_counts_the_retail_images_it_was_taken_over(self) -> None:
        # Arrange
        held = HELD

        # Act
        counted = (held["gated"] > 0, held["images"] >= held["gated"])

        # Assert
        self.assertEqual(counted, (True, True))


class CheckTest(unittest.TestCase):
    def test_a_sound_corpus_passes(self) -> None:
        # Arrange
        held = sound()

        # Act
        code, said = run_main(held)

        # Assert
        self.assertEqual((code, said.splitlines()[0]), (0, "2 images, 1 retail, 600 frames each"))

    def test_a_broken_property_fails(self) -> None:
        # Arrange
        held = {**sound(), "properties": {**sound()["properties"], census.NEVER_LOCKS: 1}}

        # Act
        code, said = run_main(held)

        # Assert
        self.assertEqual((code, f"{census.NEVER_LOCKS}: 1 broken" in said), (1, True))

    def test_a_register_counted_on_more_images_than_there_are_fails(self) -> None:
        # Arrange
        held = {**sound(), "first": {"3": 3}}

        # Act
        problems = corpus.inconsistent(held)

        # Assert
        self.assertEqual(problems, ["first 3 on 3 of 2 images"])

    def test_a_noise_setting_counted_on_more_images_than_there_are_fails(self) -> None:
        # Arrange
        held = {**sound(), "noise": {"7": 5}}

        # Act
        problems = corpus.inconsistent(held)

        # Assert
        self.assertEqual(problems, ["noise 7 on 5 of 2 images"])

    def test_more_retail_images_than_images_fails(self) -> None:
        # Arrange
        held = {**sound(), "gated": 3, "silent": 3, "zeroPeriods": 4}

        # Act
        problems = corpus.inconsistent(held)

        # Assert
        self.assertEqual(
            problems,
            ["3 retail of 2 images", "3 silent of 2 images", "4 with a zero period of 2 images"],
        )

    def test_an_inconsistent_corpus_fails_the_run(self) -> None:
        # Arrange
        held = {**sound(), "gated": 3}

        # Act
        code, said = run_main(held)

        # Assert
        self.assertEqual((code, "3 retail of 2 images" in said), (1, True))


class ReadmeTest(unittest.TestCase):
    def test_every_readme_advertises_the_census_it_holds(self) -> None:
        # Arrange
        expected = advertised(HELD)

        # Act
        found = {path.name: headline(path.read_text()) for path in READMES}

        # Assert
        self.assertEqual(found, {path.name: expected for path in READMES})

    def test_every_readme_table_holds_the_corpus_counts(self) -> None:
        # Arrange
        expected = counted_rows(HELD)

        # Act
        found = {path.name: table_rows(path.read_text(), HELD["images"]) for path in READMES}

        # Assert
        self.assertEqual(found, {path.name: expected for path in READMES})

    def test_every_readme_states_the_write_totals(self) -> None:
        # Arrange
        stated = totals(HELD)

        # Act
        missing = [
            (path.name, figure)
            for path in READMES
            for figure in stated
            if figure not in path.read_text()
        ]

        # Assert
        self.assertEqual(missing, [])

    def test_there_is_a_readme_in_every_language(self) -> None:
        # Arrange
        languages = ["README.ja.md", "README.md", "README.zh-HK.md", "README.zh-Hans.md"]

        # Act
        found = [path.name for path in READMES]

        # Assert
        self.assertEqual(found, languages)

    def test_a_table_cell_that_drifted_from_the_corpus_is_seen(self) -> None:
        # Arrange
        text = "| Seen | Images, of 2 |\n|:--|:--|\n| Never wrote | 1 |\n"

        # Act
        found = table_rows(text, 2)

        # Assert
        self.assertNotEqual(found[0], str(sound()["silent"]))

    def test_a_headline_figure_that_drifted_from_the_corpus_is_seen(self) -> None:
        # Arrange
        text = "# Title\n\n**349** images, **600** frames, **0**, **16**, **2**, **552**\n"

        # Act
        found = headline(text)

        # Assert
        self.assertNotEqual(found, advertised(HELD))


if __name__ == "__main__":
    unittest.main()
