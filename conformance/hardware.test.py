import json
import sys
import unittest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import sn76489  # noqa: E402
from sn76489 import attenuation, models, noise, tone  # noqa: E402

HELD: dict[str, Any] = json.loads((ROOT / "conformance" / "hardware.json").read_text())

FACTS: dict[str, Any] = HELD["facts"]

UNSTATED: dict[str, Any] = HELD["notStated"]

PAGES = range(1, 10)

UNSTATED_KEYS = {"value", "verified", "why", "source", "howToSettleIt", "governs"}


def value(name: str) -> Any:
    return FACTS[name]["value"]


def built(model: str) -> Any:
    return sn76489.Chip(model, seed=3)


class RecordTest(unittest.TestCase):
    def test_every_fact_names_a_document_the_record_declares(self) -> None:
        # Arrange
        declared = set(HELD["documents"])

        # Act
        unnamed = [name for name, fact in FACTS.items() if fact["document"] not in declared]

        # Assert
        self.assertEqual(unnamed, [])

    def test_every_fact_names_a_page_of_the_scan(self) -> None:
        # Arrange
        facts = FACTS

        # Act
        unpaged = [name for name, fact in facts.items() if fact.get("page") not in PAGES]

        # Assert
        self.assertEqual(unpaged, [])

    def test_every_fact_quotes_its_sentence(self) -> None:
        # Arrange
        facts = FACTS

        # Act
        silent = [name for name, fact in facts.items() if not fact.get("quote")]

        # Assert
        self.assertEqual(silent, [])

    def test_every_entry_governs_parts_the_package_models(self) -> None:
        # Arrange
        entries = {**FACTS, **UNSTATED}

        # Act
        stray = [
            name
            for name, entry in entries.items()
            if not entry.get("governs") or not set(entry["governs"]) <= set(models.MODELS)
        ]

        # Assert
        self.assertEqual(stray, [])

    def test_every_unstated_value_says_why_where_from_and_how_to_settle_it(
        self,
    ) -> None:
        # Arrange
        entries = UNSTATED

        # Act
        short = [name for name, entry in entries.items() if not set(entry) >= UNSTATED_KEYS]

        # Assert
        self.assertEqual(short, [])

    def test_no_unstated_value_claims_to_be_verified(self) -> None:
        # Arrange
        entries = UNSTATED

        # Act
        claimed = [name for name, entry in entries.items() if entry["verified"] is not False]

        # Assert
        self.assertEqual(claimed, [])


class FactTest(unittest.TestCase):
    def test_the_prescale_is_what_the_data_sheet_prints_for_each_part(self) -> None:
        # Arrange
        printed = value("prescale")

        # Act
        modelled = {name: model.prescale for name, model in models.MODELS.items()}

        # Assert
        self.assertEqual(modelled, printed)

    def test_the_load_time_is_what_the_data_sheet_prints_for_each_part(self) -> None:
        # Arrange
        printed = value("loadClocks")

        # Act
        modelled = {name: model.load_clocks for name, model in models.MODELS.items()}

        # Assert
        self.assertEqual(modelled, printed)

    def test_the_tone_counter_has_the_printed_number_of_stages(self) -> None:
        # Arrange
        printed = value("toneCounter")["bits"]

        # Act
        modelled = tone.PERIOD_BITS

        # Assert
        self.assertEqual(modelled, printed)

    def test_the_counter_decrements_once_per_printed_number_of_input_clocks(
        self,
    ) -> None:
        # Arrange
        part = built("sn76489an")
        before = part.ticks

        # Act
        part.clock()

        # Assert
        self.assertEqual(part.ticks - before, value("toneCounter")["decrementsPerInputClocks"])

    def test_the_fields_have_the_printed_widths(self) -> None:
        # Arrange
        printed = value("toneFields")

        # Act
        modelled = {
            "frequencyBits": tone.PERIOD_BITS,
            "attenuationBits": attenuation.OFF.bit_length(),
        }

        # Assert
        self.assertEqual(modelled, printed)

    def test_the_largest_attenuation_short_of_off_is_the_printed_maximum(self) -> None:
        # Arrange
        steps = range(attenuation.OFF)

        # Act
        largest = max(attenuation.decibels(step) for step in steps)

        # Assert
        self.assertEqual(largest, value("attenuationMaximum"))

    def test_the_fixed_noise_rates_are_the_printed_ones(self) -> None:
        # Arrange
        prescale = value("prescale")["sn76489an"]

        # Act
        modelled = [rate * prescale for rate in noise.RATES]

        # Assert
        self.assertEqual(modelled, value("noiseRates"))

    def test_a_noise_write_clears_the_shift_register(self) -> None:
        # Arrange
        part = built("sn76489an")

        # Act
        part.write(0xE4)

        # Assert
        self.assertEqual(part.shift, UNSTATED["shiftRegister"]["value"]["clearedTo"])

    def test_no_reachable_shift_state_is_zero(self) -> None:
        # Arrange
        register = noise.TOP
        seen = set()

        # Act
        for _ in range(1 << noise.WIDTH):
            register = noise.shifted(register, white=True)
            seen.add(register)

        # Assert
        self.assertNotIn(0, seen)

    def test_there_are_as_many_registers_as_the_field_addresses(self) -> None:
        # Arrange
        printed = value("registerField")

        # Act
        addressable = 1 << printed["fieldBits"]

        # Assert
        self.assertEqual(addressable, printed["registers"])

    def test_a_second_byte_reaches_the_six_most_significant_bits(self) -> None:
        # Arrange
        part = built("sn76489an")
        part.write(0x80)

        # Act
        part.write(0x3F)

        # Assert
        self.assertEqual(part.periods[0].bit_length() - tone.LOW_BITS, value("secondByte"))


class UnstatedTest(unittest.TestCase):
    def test_the_shift_register_is_the_width_its_record_gives(self) -> None:
        # Arrange
        recorded = UNSTATED["shiftRegister"]["value"]

        # Act
        modelled = (noise.WIDTH, noise.TOP)

        # Assert
        self.assertEqual(modelled, (recorded["bits"], recorded["clearedTo"]))

    def test_a_zero_period_lasts_as_long_as_its_record_says(self) -> None:
        # Arrange
        counter = 0
        steps = 0

        # Act
        while True:
            counter = tone.counted(counter)
            steps += 1
            if counter == 0:
                break

        # Assert
        self.assertEqual(steps, UNSTATED["zeroPeriod"]["value"])


if __name__ == "__main__":
    unittest.main()
