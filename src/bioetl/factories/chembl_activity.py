"""Deprecated - use bioetl.interfaces.factories.chembl_activity instead."""

import warnings

warnings.warn(
    "bioetl.factories.chembl_activity is deprecated. "
    "Use bioetl.interfaces.factories.chembl_activity instead.",
    DeprecationWarning,
    stacklevel=2,
)

from bioetl.interfaces.factories.chembl_activity import *  # noqa: F401, F403, E402
from bioetl.interfaces.factories.chembl_activity import (  # noqa: F401, E402
    ChEMBLActivityPipelineFactory,
)

__all__ = ["ChEMBLActivityPipelineFactory"]
