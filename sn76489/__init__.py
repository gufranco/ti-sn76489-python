from typing import Any

from . import attenuation as attenuation
from . import core as core
from . import errors as errors
from . import models as models
from . import noise as noise
from . import tone as tone
from .core import UNSET_SEED
from .errors import UnknownModelError
from .models import MODELS, Model
from .version import VERSION

__version__ = VERSION


def Chip(model: str | None = None, **options: Any) -> "core.Chip":  # noqa: N802
    built = core.Chip(models.lookup(model), seed=options.get("seed", UNSET_SEED))
    return built


__all__ = [
    "MODELS",
    "UNSET_SEED",
    "Chip",
    "Model",
    "UnknownModelError",
    "__version__",
]
