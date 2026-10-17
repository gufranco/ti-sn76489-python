PERIOD_BITS = 10

PERIOD_MASK = (1 << PERIOD_BITS) - 1

LOW_BITS = 4

LOW_MASK = (1 << LOW_BITS) - 1

HIGH_MASK = 0x3F


def with_low(period: int, value: int) -> int:
    return (period & ~LOW_MASK & PERIOD_MASK) | (value & LOW_MASK)


def with_high(period: int, value: int) -> int:
    return (period & LOW_MASK) | ((value & HIGH_MASK) << LOW_BITS)


def counted(counter: int) -> int:
    return (counter - 1) & PERIOD_MASK
