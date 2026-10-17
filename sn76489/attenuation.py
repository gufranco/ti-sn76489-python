OFF = 0x0F

WEIGHTS_DB = (16, 8, 4, 2)


def decibels(step: int) -> int:
    return sum(weight for bit, weight in enumerate(WEIGHTS_DB) if step & (0x08 >> bit))


def gain(step: int) -> float:
    if step & OFF == OFF:
        return 0.0
    return float(10 ** (-decibels(step) / 20))
