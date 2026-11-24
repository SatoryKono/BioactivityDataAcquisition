"""Typed post-join merge state and persist request models."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

import polars as pl

from bioetl.domain.composite import EnricherConfig
from bioetl.domain.composite.cross_validation import CrossValidationStats

__all__ = ["MergePersistRequest", "MergePostJoinContext"]


@dataclass(frozen=True, slots=True)
class MergePostJoinContext:
    """Post-join merge state ready for persistence and result assembly."""

    merged_df: pl.DataFrame
    records_merged: int
    records_enriched: int
    cv_stats: CrossValidationStats | None
    quarantine_payloads: list[dict[str, object]]
    classification_pending_indices: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class MergePersistRequest:
    """Bounded arguments for merge persistence and result assembly."""

    merged_df: pl.DataFrame
    enrichers: Sequence[EnricherConfig]
    records_merged: int
    records_from_seed: int
    records_enriched: int
    sources_used: list[str]
    cv_stats: CrossValidationStats | None
    quarantine_payloads: list[dict[str, object]]
    metadata_timestamp: datetime | None
    run_id: str
    started_at: datetime
    started_monotonic: float
    classification_pending_indices: tuple[int, ...] = ()
