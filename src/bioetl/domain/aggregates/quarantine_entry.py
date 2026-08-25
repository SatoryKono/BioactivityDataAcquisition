"""QuarantineEntry public compatibility facade."""

from __future__ import annotations

from bioetl.domain.aggregates._quarantine_aggregate import (
    QuarantineEntry as QuarantineEntry,
)
from bioetl.domain.aggregates._quarantine_value_objects import (
    QuarantineStatus,
    ResolutionInfo,
)

__all__ = ["QuarantineEntry", "QuarantineStatus", "ResolutionInfo"]
