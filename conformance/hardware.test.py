import json
import math
import sys
import unittest
from itertools import pairwise
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import sn76489  # noqa: E402

HELD: dict[str, Any] = json.loads((ROOT / "conformance" / "hardware.json").read_text())

FACTS: dict[str, Any] = HELD["facts"]

UNSTATED: dict[str, Any] = HELD["notStated"]

PAGES = range(1, 10)

UNSTATED_KEYS = {"value", "verified", "why", "source", "howToSettleIt", "governs"}

EDGE_LIMIT = 1 << 18

LOAD_LIMIT = 1 << 8

SHIFT_LIMIT = 1 << 22

TONE_ONE = 0x80

TONE_ONE_LEVEL = 0x90

TONE_THREE = 0xC0

WHITE_AT_512 = 0xE4

PUBLIC_STATE = ("ready", "loading", "periods", "steps", "control", "shift", "latched", "bits")


def value(name: str) -> Any:
    return FACTS[name]["value"]


def built(model: str) -> Any:
    return sn76489.Chip(model, seed=3)


def loaded(model: str, *values: int) -> Any:
    part = built(model)
    for one in values:
        held_low(part, one)
    return part


def held_low(part: Any, byte: int) -> int:
    part.write(byte)
    clocks = 0
    while not part.ready and clocks < LOAD_LIMIT:
        part.tick()
        clocks += 1
    return clocks


def edges(part: Any, count: int) -> list[int]:
    found: list[int] = []
    limit = part.ticks + EDGE_LIMIT
    while len(found) < count and part.ticks < limit:
        before = part.bits[0]
        part.tick()
        if part.bits[0] != before:
            found.append(part.ticks)
    return found


def shift_gaps(part: Any, count: int) -> set[int]:
    found: list[int] = []
    limit = part.ticks + SHIFT_LIMIT
    while len(found) < count and part.ticks < limit:
        before = part.shift
        part.tick()
        if part.shift != before:
            found.append(part.ticks)
    return {later - earlier for earlier, later in pairwise(found[1:])}


def registers_seen(part: Any, shifts: int) -> set[int]:
    seen: set[int] = set()
    limit = part.ticks + SHIFT_LIMIT
    while len(seen) < shifts and part.ticks < limit:
        before = part.shift
        part.tick()
        if part.shift != before:
            seen.add(part.shift)
    return seen


def state(part: Any) -> tuple[Any, ...]:
    return tuple(
        list(getattr(part, name)) if isinstance(getattr(part, name), list) else getattr(part, name)
        for name in PUBLIC_STATE
    )


def ticks_per_period(model: str) -> int:
    part = built(model)
    before = part.ticks
    part.clock()
    return int(part.ticks - before)


def gain_at(step: int) -> float:
    part = built("sn76489an")
    part.write(TONE_ONE_LEVEL | step)
    return float(part.gains[0])


def latched_after(first_byte: int) -> int:
    part = built("sn76489an")
    part.write(first_byte)
    return int(part.latched)


def decibels(gain: float) -> int:
    return round(-20 * math.log10(gain))


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
            if not entry.get("governs") or not set(entry["governs"]) <= set(sn76489.MODELS)
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
        names = sorted(sn76489.MODELS)

        # Act
        spent = {name: ticks_per_period(name) for name in names}

        # Assert
        self.assertEqual(spent, value("prescale"))

    def test_the_load_time_is_what_the_data_sheet_prints_for_each_part(self) -> None:
        # Arrange
        parts = {name: built(name) for name in sn76489.MODELS}

        # Act
        held = {name: held_low(part, TONE_ONE_LEVEL) for name, part in parts.items()}

        # Assert
        self.assertEqual(held, value("loadClocks"))

    def test_the_tone_counter_has_the_printed_number_of_stages(self) -> None:
        # Arrange
        part = loaded("sn76489an", TONE_ONE | 0x0F)

        # Act
        part.write(0x3F)

        # Assert
        self.assertEqual(part.periods[0].bit_length(), value("toneCounter")["bits"])

    def test_the_counter_decrements_once_per_printed_number_of_input_clocks(
        self,
    ) -> None:
        # Arrange
        part = loaded("sn76489an", TONE_ONE | 1, 0)

        # Act
        found = edges(part, 3)

        # Assert
        self.assertEqual(found[2] - found[1], value("toneCounter")["decrementsPerInputClocks"])

    def test_the_fields_have_the_printed_widths(self) -> None:
        # Arrange
        part = loaded("sn76489an", TONE_ONE | 0x0F, 0x3F)

        # Act
        part.write(TONE_ONE_LEVEL | 0x0F)

        # Assert
        self.assertEqual(
            {
                "frequencyBits": part.periods[0].bit_length(),
                "attenuationBits": part.steps[0].bit_length(),
            },
            value("toneFields"),
        )

    def test_the_largest_attenuation_short_of_off_is_the_printed_maximum(self) -> None:
        # Arrange
        steps = range(15)

        # Act
        gains = [gain_at(step) for step in steps]

        # Assert
        self.assertEqual(decibels(min(gains)), value("attenuationMaximum"))

    def test_the_fixed_noise_rates_are_the_printed_ones(self) -> None:
        # Arrange
        controls = (WHITE_AT_512, WHITE_AT_512 | 1, WHITE_AT_512 | 2)

        # Act
        found = [shift_gaps(loaded("sn76489an", control), 4) for control in controls]

        # Assert
        self.assertEqual(found, [{rate} for rate in value("noiseRates")])

    def test_a_noise_write_clears_the_shift_register(self) -> None:
        # Arrange
        part = built("sn76489an")
        cleared = value("noiseCleared")

        # Act
        part.write(WHITE_AT_512)

        # Assert
        self.assertEqual(part.shift == UNSTATED["shiftRegister"]["value"]["clearedTo"], cleared)

    def test_no_reachable_shift_state_is_zero(self) -> None:
        # Arrange
        part = loaded("sn76494n", TONE_THREE | 1, 0, WHITE_AT_512 | 3)
        width = UNSTATED["shiftRegister"]["value"]["bits"]

        # Act
        seen = registers_seen(part, (1 << width) - 1)

        # Assert
        self.assertEqual(0 not in seen, value("noiseNeverLocks"))

    def test_there_are_as_many_registers_as_the_field_addresses(self) -> None:
        # Arrange
        printed = value("registerField")

        # Act
        reached = {latched_after(0x80 | one << 4) for one in range(1 << printed["fieldBits"])}

        # Assert
        self.assertEqual(len(reached), printed["registers"])

    def test_a_second_byte_reaches_the_six_most_significant_bits(self) -> None:
        # Arrange
        part = built("sn76489an")
        part.write(TONE_ONE)

        # Act
        part.write(0x3F)

        # Assert
        self.assertEqual(bin(part.periods[0]).count("1"), value("secondByte"))

    def test_ready_stays_low_for_the_printed_load_time(self) -> None:
        # Arrange
        parts = {name: built(name) for name in sn76489.MODELS}

        # Act
        held = {name: held_low(part, 0x9F) for name, part in parts.items()}

        # Assert
        self.assertEqual(held, value("loadClocks"), value("ready"))

    def test_a_borrow_toggles_the_flip_flop_and_reloads_the_counter(self) -> None:
        # Arrange
        part = loaded("sn76489an", TONE_ONE | 5, 0)

        # Act
        found = edges(part, 4)

        # Assert
        self.assertEqual(
            {found[2] - found[1], found[3] - found[2]},
            {part.periods[0] * value("prescale")["sn76489an"]},
            value("toneBorrow"),
        )

    def test_a_full_cycle_lasts_twice_the_period(self) -> None:
        # Arrange
        part = loaded("sn76489an", TONE_ONE | 5, 0)

        # Act
        found = edges(part, 3)

        # Assert
        self.assertEqual(
            (found[2] - found[0]) // value("prescale")["sn76489an"],
            2 * part.periods[0],
            value("tonePeriod"),
        )

    def test_the_address_stays_latched_for_every_later_data_byte(self) -> None:
        # Arrange
        part = loaded("sn76489an", TONE_ONE, 0x01)

        # Act
        part.write(0x02)

        # Assert
        self.assertEqual(part.periods[0] == 0x020, value("latchedAddress"))

    def test_with_no_reset_pin_a_reset_changes_nothing(self) -> None:
        # Arrange
        part = built("sn76489an")
        before = state(part)

        # Act
        returned = part.reset()

        # Assert
        self.assertEqual((returned is part, state(part) == before), (True, True), value("reset"))


class UnstatedTest(unittest.TestCase):
    def test_the_shift_register_is_the_width_its_record_gives(self) -> None:
        # Arrange
        recorded = UNSTATED["shiftRegister"]["value"]
        part = built("sn76489an")

        # Act
        part.write(WHITE_AT_512)

        # Assert
        self.assertEqual(part.shift, 1 << (recorded["bits"] - 1))

    def test_a_zero_period_lasts_as_long_as_its_record_says(self) -> None:
        # Arrange
        part = loaded("sn76489an", TONE_ONE, 0)

        # Act
        found = edges(part, 3)

        # Assert
        self.assertEqual(
            (found[2] - found[1]) // value("prescale")["sn76489an"],
            UNSTATED["zeroPeriod"]["value"],
        )


if __name__ == "__main__":
    unittest.main()
