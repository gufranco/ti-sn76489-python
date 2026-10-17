from collections.abc import Sequence
from typing import override

from sn76489.errors import UnknownModelError


class Model:
    __slots__ = ("aliases", "load_clocks", "name", "prescale", "summary")

    def __init__(
        self,
        name: str,
        summary: str,
        prescale: int,
        load_clocks: int,
        aliases: Sequence[str] = (),
    ) -> None:
        self.name = name
        self.summary = summary
        self.prescale = prescale
        self.load_clocks = load_clocks
        self.aliases = tuple(aliases)

    @override
    def __repr__(self) -> str:
        return f"<Model {self.name}, divide by {self.prescale}, {self.load_clocks} clocks to load>"


_CATALOGUE = (
    Model(
        name="sn76489an",
        summary=(
            "The SN76489AN: the input clock divided by 16 before the generators, "
            "and 32 input clocks to load a byte."
        ),
        prescale=16,
        load_clocks=32,
        aliases=("sn76489a", "76489an", "76489a"),
    ),
    Model(
        name="sn76494n",
        summary=(
            "The SN76494N: the SN76489AN without its divide-by-eight stage, so the "
            "input clock is divided by 2 and a byte loads in 4 input clocks."
        ),
        prescale=2,
        load_clocks=4,
        aliases=("sn76494", "76494n", "76494"),
    ),
)

MODELS = {model.name: model for model in _CATALOGUE}

_BY_ALIAS = {alias: model for model in _CATALOGUE for alias in (model.name, *model.aliases)}


def _normalise(name: str) -> str:
    return str(name).strip().lower().replace("-", "").replace("_", "")


def lookup(name: str | None) -> Model:
    if name is None:
        raise UnknownModelError(
            "no model was named, and this package will not choose one for you."
            f" Name one of: {', '.join(sorted(MODELS))}"
        )
    found = _BY_ALIAS.get(_normalise(name))
    if found is None:
        raise UnknownModelError(
            f"{name} is not a model this package covers; it has {', '.join(sorted(MODELS))}"
        )
    return found
