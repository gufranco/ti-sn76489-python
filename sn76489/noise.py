WIDTH = 15

TOP = 1 << (WIDTH - 1)

WHITE = 0x04

TONE_THREE = 0x03

RATE_SELECT = 0x03

CONTROL_MASK = 0x07

RATES = (32, 64, 128)


def shifted(register: int, white: bool) -> int:
    feedback = (register ^ (register >> 1)) & 1 if white else register & 1
    return (register >> 1) | (TOP if feedback else 0)


def is_white(control: int) -> bool:
    return bool(control & WHITE)


def follows_tone_three(control: int) -> bool:
    return control & RATE_SELECT == TONE_THREE


def rate(control: int) -> int:
    return RATES[control & RATE_SELECT]
