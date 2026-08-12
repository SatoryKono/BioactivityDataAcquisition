"""Merge result model for composite pipelines."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.immutability import deep_freeze_json, freeze_fields
from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.composite.cross_validation import CrossValidationStats

__all__ = ["MergeResult"]


def _reject_negative_counts(pairs: tuple[tuple[str, int], ...]) -> None:
    for name, value in pairs:
        if value < 0:
            raise ValueError(f"{name} must be >= 0, got {value}")


def _reject_inconsistent_enrichment(
    records_merged: int, records_enriched: int, records_fully_enriched: int
) -> None:
    if records_fully_enriched > records_enriched:
        raise ValueError(
            "records_fully_enriched cannot exceed records_enriched: "
            f"{records_fully_enriched} > {records_enriched}"
        )
    if records_enriched > records_merged > 0:
        raise ValueError(
            "records_enriched cannot exceed records_merged: "
            f"{records_enriched} > {records_merged}"
        )


def _reject_non_finite_duration(duration_seconds: float) -> None:
    if not math.isfinite(duration_seconds):
        raise ValueError(
            f"duration_seconds must be finite, got {duration_seconds}"
        )
    if duration_seconds < 0:
        raise ValueError(
            f"duration_seconds must be >= 0, got {duration_seconds}"
        )


@dataclass(frozen=True, slots=True)
class MergeResult:
    """Result of merge operation."""

    records_merged: int = 0
    records_from_seed: int = 0
    records_enriched: int = 0
    records_fully_enriched: int = 0
    sources_used: tuple[str, ...] = ()
    field_coverage: dict[str, float] = field(default_factory=dict)
    duration_seconds: float = 0.0
    output_silver_path: str | None = None
    output_gold_path: str | None = None
    lineage_summary: dict[str, int] = field(default_factory=dict)
    cross_validation_stats: CrossValidationStats | None = None
    quarantine_payloads: tuple[JsonDict, ...] = ()

    def _validate_counts(self) -> None:
        """Reject negative counters and inconsistent enrichment totals."""
        _reject_negative_counts(
            (
                ("records_merged", self.records_merged),
                ("records_from_seed", self.records_from_seed),
                ("records_enriched", self.records_enriched),
                ("records_fully_enriched", self.records_fully_enriched),
            )
        )
        _reject_inconsistent_enrichment(
            self.records_merged,
            self.records_enriched,
            self.records_fully_enriched,
        )
        _reject_non_finite_duration(self.duration_seconds)

    def __post_init__(self) -> None:
        """Freeze nested mappings/payloads so callers cannot mutate state."""
        self._validate_counts()
        if isinstance(self.sources_used, list):
            object.__setattr__(self, "sources_used", tuple(self.sources_used))
        payloads = (
            tuple(self.quarantine_payloads)
            if isinstance(self.quarantine_payloads, list)
            else self.quarantine_payloads
        )
        object.__setattr__(
            self,
            "quarantine_payloads",
            tuple(deep_freeze_json(payload) for payload in payloads),
        )
        freeze_fields(self, ("field_coverage", "lineage_summary"))

    @property
    def enrichment_rate(self) -> float:
        """Calculate overall enrichment rate."""
        return (
            self.records_enriched / self.records_merged if self.records_merged else 0.0
        )
