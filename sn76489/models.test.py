import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import unittest  # noqa: E402

import sn76489  # noqa: E402


class CatalogueTest(unittest.TestCase):
    def test_it_covers_the_two_parts_the_data_sheet_documents(self) -> None:
        # Arrange
        catalogue = sn76489.MODELS

        # Act
        names = sorted(catalogue)

        # Assert
        self.assertEqual(names, ["sn76489an", "sn76494n"])

    def test_the_sn76489an_divides_its_input_clock_by_16(self) -> None:
        # Arrange
        part = sn76489.Chip("sn76489an")

        # Act
        divided = part.part.prescale

        # Assert
        self.assertEqual(divided, 16)

    def test_the_sn76494n_lacks_the_divide_by_eight_stage(self) -> None:
        # Arrange
        part = sn76489.Chip("sn76494n")

        # Act
        divided = part.part.prescale

        # Assert
        self.assertEqual(divided, 2)

    def test_a_byte_loads_in_32_clocks_on_one_and_4_on_the_other(self) -> None:
        # Arrange
        catalogue = sn76489.MODELS

        # Act
        loads = {name: model.load_clocks for name, model in catalogue.items()}

        # Assert
        self.assertEqual(loads, {"sn76489an": 32, "sn76494n": 4})

    def test_a_model_describes_itself(self) -> None:
        # Arrange
        model = sn76489.MODELS["sn76494n"]

        # Act
        described = repr(model)

        # Assert
        self.assertEqual(described, "<Model sn76494n, divide by 2, 4 clocks to load>")

    def test_every_entry_is_a_model(self) -> None:
        # Arrange
        catalogue = sn76489.MODELS

        # Act
        kinds = {type(model) for model in catalogue.values()}

        # Assert
        self.assertEqual(kinds, {sn76489.Model})


class LookupTest(unittest.TestCase):
    def test_a_name_is_found_however_it_is_written(self) -> None:
        # Arrange
        names = ("SN76489AN", "sn-76489a", " 76489_a ")

        # Act
        found = {sn76489.Chip(name).model for name in names}

        # Assert
        self.assertEqual(found, {"sn76489an"})

    def test_no_name_is_refused_rather_than_guessed(self) -> None:
        # Arrange
        def attempt() -> Any:
            return sn76489.Chip()

        # Act
        with self.assertRaises(sn76489.UnknownModelError) as raised:
            attempt()

        # Assert
        self.assertIn("will not choose one for you", str(raised.exception))

    def test_an_unknown_name_lists_the_parts_there_are(self) -> None:
        # Arrange
        def attempt() -> Any:
            return sn76489.Chip("sn76496")

        # Act
        with self.assertRaises(sn76489.UnknownModelError) as raised:
            attempt()

        # Assert
        self.assertIn("sn76489an, sn76494n", str(raised.exception))


if __name__ == "__main__":
    unittest.main()
