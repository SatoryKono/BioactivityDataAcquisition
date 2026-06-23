"""Models/constants for organism classification service."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Final

from bioetl.domain.types import CellularityType

_DEFAULT_ORGANISM_FIELD: Final[str] = "assay_organism"
_DEFAULT_TAXONOMY_ID_FIELD: Final[str] = "assay_tax_id"
_OUT_CELLULARITY: Final[str] = "organism_class"
_OUT_NORMALIZED_ORGANISM: Final[str] = "normalized_organism"
_OUT_CLASSIFICATION_SOURCE: Final[str] = "classification_source"

CellularityFilterStrategy = Callable[[CellularityType | None], bool]

__all__ = [
    "_DEFAULT_ORGANISM_FIELD",
    "_DEFAULT_TAXONOMY_ID_FIELD",
    "_OUT_CELLULARITY",
    "_OUT_CLASSIFICATION_SOURCE",
    "_OUT_NORMALIZED_ORGANISM",
    "CellularityFilterStrategy",
    "ClassificationStats",
]


@dataclass(frozen=True, slots=True)
class ClassificationStats:
    """Aggregated classification statistics for a batch of records."""

    total: int
    acellular: int
    unicellular: int
    multicellular: int
    unresolved: int
    conflict_count: int

    @property
    def resolved_count(self) -> int:
        """Number of successfully classified records."""
        return self.total - self.unresolved

    @property
    def resolution_rate(self) -> float:
        """Fraction of records successfully classified (0.0–1.0)."""
        if self.total == 0:
            return 0.0
        return self.resolved_count / self.total
