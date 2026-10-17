import random
from typing import Any

from sn76489 import attenuation, noise, tone

UNSET_SEED = 0x76489

LATCH = 0x80

REGISTER_SHIFT = 4

REGISTER_MASK = 0x07

DATA_MASK = 0x0F

TONES = 3

CHANNELS = 4

NOISE_REGISTER = 6

TONE_THREE = 2


class Chip:
    __slots__ = (
        "control",
        "counters",
        "flips",
        "latched",
        "loading",
        "model",
        "noise_count",
        "part",
        "periods",
        "phase",
        "shift",
        "steps",
        "ticks",
    )

    def __init__(self, part: Any, seed: int = UNSET_SEED) -> None:
        scrambled = random.Random(seed)
        self.part = part
        self.model: str = part.name
        self.periods = [scrambled.randrange(tone.PERIOD_MASK + 1) for _ in range(TONES)]
        self.counters = [scrambled.randrange(tone.PERIOD_MASK + 1) for _ in range(TONES)]
        self.flips = [scrambled.randrange(2) for _ in range(TONES)]
        self.steps = [scrambled.randrange(attenuation.OFF + 1) for _ in range(CHANNELS)]
        self.control = scrambled.randrange(noise.CONTROL_MASK + 1)
        self.shift = scrambled.randrange(1, noise.TOP << 1)
        self.noise_count = scrambled.randrange(noise.RATES[-1])
        self.latched = scrambled.randrange(REGISTER_MASK + 1)
        self.phase = scrambled.randrange(part.prescale)
        self.loading = 0
        self.ticks = 0

    def reset(self) -> "Chip":
        return self

    @property
    def ready(self) -> bool:
        return self.loading == 0

    @property
    def bits(self) -> tuple[int, int, int, int]:
        return (self.flips[0], self.flips[1], self.flips[2], self.shift & 1)

    @property
    def gains(self) -> tuple[float, ...]:
        return tuple(attenuation.gain(step) for step in self.steps)

    @property
    def level(self) -> float:
        return sum(gain for bit, gain in zip(self.bits, self.gains, strict=True) if bit)

    def write(self, value: int) -> None:
        if value & LATCH:
            self.latched = (value >> REGISTER_SHIFT) & REGISTER_MASK
            self._first(value & DATA_MASK)
        else:
            self._second(value)
        self.loading = self.part.load_clocks

    def _first(self, data: int) -> None:
        register = self.latched
        if register == NOISE_REGISTER:
            self._noise(data)
        elif register & 1:
            self.steps[register >> 1] = data
        else:
            self.periods[register >> 1] = tone.with_low(self.periods[register >> 1], data)

    def _second(self, value: int) -> None:
        register = self.latched
        if register & 1 or register == NOISE_REGISTER:
            self._first(value & DATA_MASK)
        else:
            self.periods[register >> 1] = tone.with_high(self.periods[register >> 1], value)

    def _noise(self, data: int) -> None:
        self.control = data & noise.CONTROL_MASK
        self.shift = noise.TOP

    def tick(self) -> None:
        self.ticks += 1
        if self.loading:
            self.loading -= 1
        self.phase = (self.phase + 1) % self.part.prescale
        if self.phase == 0:
            self._period()

    def clock(self) -> None:
        for _ in range(self.part.prescale):
            self.tick()

    def _period(self) -> None:
        rose = False
        for channel in range(TONES):
            self.counters[channel] = tone.counted(self.counters[channel])
            if self.counters[channel] == 0:
                self.flips[channel] ^= 1
                self.counters[channel] = self.periods[channel]
                rose = rose or (channel == TONE_THREE and self.flips[channel] == 1)
        self._noise_period(rose)

    def _noise_period(self, tone_three_rose: bool) -> None:
        if noise.follows_tone_three(self.control):
            due = tone_three_rose
        else:
            self.noise_count = (self.noise_count + 1) % noise.rate(self.control)
            due = self.noise_count == 0
        if due:
            self.shift = noise.shifted(self.shift, noise.is_white(self.control))
