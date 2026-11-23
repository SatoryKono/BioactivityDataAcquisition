"""Persistence tail of composite post-join finalization."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

import polars as pl

from bioetl.application.composite.helpers.target_classification_stage import (
    commit_joined_classification,
)
from bioetl.application.composite.merger_post_join import (
    MergePostJoinWorkflowContext,
    _bound_classification_stage,
)
from bioetl.application.runtime_timestamps import derive_completion_timestamp
from bioetl.domain.composite import EnricherConfig
from bioetl.domain.composite.cross_validation import CrossValidationStats
from bioetl.domain.composite.result import MergeResult


async def persist_and_build_result(
    host: MergePostJoinWorkflowContext,
    *,
    merged_df: pl.DataFrame,
    enrichers: Sequence[EnricherConfig],
    records_merged: int,
    records_from_seed: int,
    records_enriched: int,
    sources_used: list[str],
    cv_stats: CrossValidationStats | None,
    quarantine_payloads: list[dict[str, object]],
    metadata_timestamp: datetime | None,
    run_id: str,
    started_at: datetime,
    started_monotonic: float,
) -> MergeResult:
    """Persist merge outputs and build the domain ``MergeResult``."""
    stage = _bound_classification_stage(host)

    async def _write() -> None:
        await host._write_outputs(
            merged_df,
            metadata_timestamp=metadata_timestamp,
            run_id=run_id,
            sources_used=sources_used,
        )

    await commit_joined_classification(stage, run_id, _write)
    _, duration = derive_completion_timestamp(
        started_at=started_at,
        started_monotonic=started_monotonic,
    )
    host._logger.info(
        "Merge completed",
        records_merged=records_merged,
        sources_used=sources_used,
        duration_seconds=duration,
    )
    return host._build_merge_result(
        merged_df=merged_df,
        enrichers=enrichers,
        records_merged=records_merged,
        records_from_seed=records_from_seed,
        records_enriched=records_enriched,
        sources_used=sources_used,
        duration_seconds=duration,
        cv_stats=cv_stats,
        quarantine_payloads=quarantine_payloads,
    )
