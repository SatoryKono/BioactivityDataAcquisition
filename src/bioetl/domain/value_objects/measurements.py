"""Backward-compatibility module for activity_values.py.

.. deprecated:: 1.0.0
    This module is deprecated. Use `activity_values` instead.
    The term 'measurements' is deprecated in favor of 'activity' per glossary.md.

All symbols are re-exported from activity_values for backward compatibility.
A deprecation warning is issued when this module is imported.

Example:
    # Deprecated (will show warning):
    from bioetl.domain.value_objects.measurements import Concentration

    # Preferred:
    from bioetl.domain.value_objects.activity_values import Concentration
    # Or via the package:
    from bioetl.domain.value_objects import Concentration
"""

import warnings

warnings.warn(
    "bioetl.domain.value_objects.measurements is deprecated. "
    "Use bioetl.domain.value_objects.activity_values instead. "
    "See glossary.md for Ubiquitous Language terminology.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export all symbols for backward compatibility
from bioetl.domain.value_objects.activity_values import (  # noqa: E402
    ActivityType,
    Concentration,
    ConcentrationUnit,
    PChemblValue,
)

__all__ = [
    "ActivityType",
    "Concentration",
    "ConcentrationUnit",
    "PChemblValue",
]
