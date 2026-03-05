"""QuarantineEntry Aggregate.

Re-export facade: actual definitions live in sub-modules
(_quarantine_value_objects, _quarantine_aggregate).
"""

from bioetl.domain.aggregates._quarantine_aggregate import QuarantineEntry
from bioetl.domain.aggregates._quarantine_value_objects import (
    QuarantineStatus,
    ResolutionInfo,
)

__all__ = [
    "QuarantineEntry",
    "QuarantineStatus",
    "ResolutionInfo",
]
