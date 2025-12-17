"""Deprecated - use bioetl.interfaces.bootstrap instead."""

import warnings

warnings.warn(
    "bioetl.bootstrap is deprecated. Use bioetl.interfaces.bootstrap instead.",
    DeprecationWarning,
    stacklevel=2,
)

from bioetl.interfaces.bootstrap import *  # noqa: F401, F403, E402
from bioetl.interfaces.bootstrap import __all__  # noqa: F401, E402
