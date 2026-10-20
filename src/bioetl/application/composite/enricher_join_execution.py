"""Execution helpers for enricher join preparation and execution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import polars as pl

from bioetl.application.composite.enricher_fallback_join import (
    execute_fallback_enricher_join,
)
from bioetl.application.composite.join_execution import JoinHow
from bioetl.application.composite.join_planner_helpers import (
    EnricherJoinMetadataContext,
    PrepareJoinFramesContext,
    build_enricher_join_metadata,
    prepare_join_frames,
)

if TYPE_CHECKING:
    from bioetl.application.composite.aggregator import EnricherAggregator
    from bioetl.application.composite.column_renamer import ColumnRenamer
    from bioetl.application.composite.conflict_resolver import ConflictResolverService
    from bioetl.application.composite.deduplication import EnricherDeduplicatorService
    from bioetl.application.composite.protocols import JoinKeyResolverProtocol
    from bioetl.domain.composite import EnricherConfig
    from bioetl.domain.ports import LoggerPort


@dataclass(frozen=True, slots=True)
class PreparedEnricherJoinContext:
    """Prepared context for executing one enricher join."""

    enricher_pipeline: str
    metadata: EnricherJoinMetadataContext
    merged_df: pl.DataFrame
    enricher_df: pl.DataFrame
    required: bool = False


def prepare_enricher_dataframe(
    *,
    enricher_df: pl.DataFrame,
    enricher: EnricherConfig,
    aggregator: EnricherAggregator,
) -> pl.DataFrame:
    """Prepare raw enricher frame before join orchestration."""
    if enricher.is_many_to_one and enricher.aggregation is not None:
        return aggregator.aggregate(
            enricher_df,
            enricher.aggregation,
            enricher.pipeline,
        )
    return enricher_df


def build_prepared_enricher_join_context(
    *,
    merged_df: pl.DataFrame,
    enricher_df: pl.DataFrame,
    enricher: EnricherConfig,
    seed_pipeline: str | None,
    deduplicator: EnricherDeduplicatorService,
    aggregator: EnricherAggregator,
    renamer: ColumnRenamer,
    logger: LoggerPort,
    field_alias_resolver: Callable[[str], dict[str, str] | None],
    join_key_resolver: JoinKeyResolverProtocol,
    resolve_join_key_names: Callable[
        [str, str | None, str, list[str]], tuple[str, str, str | None]
    ],
    drop_system_columns: Callable[[pl.DataFrame], pl.DataFrame],
) -> PreparedEnricherJoinContext:
    """Build prepared enricher join context before conflict resolution."""
    metadata = build_enricher_join_metadata(
        join_keys=enricher.join_keys,
        primary_join_key=enricher.primary_join_key,
        enricher_pipeline=enricher.pipeline,
        seed_pipeline=seed_pipeline,
        merged_columns=merged_df.columns,
        resolve_join_key_names=resolve_join_key_names,
    )
    prepared_enricher_df = prepare_enricher_dataframe(
        enricher_df=enricher_df,
        enricher=enricher,
        aggregator=aggregator,
    )
    prepared_merged_df, prepared_enricher_df = prepare_join_frames(
        PrepareJoinFramesContext(
            merged_df=merged_df,
            right_df=prepared_enricher_df,
            left_join_keys=metadata.join_keys_list,
            right_join_keys=metadata.join_keys_list,
            right_pipeline=enricher.pipeline,
            seed_pipeline=seed_pipeline,
            deduplicator=deduplicator,
            join_key_resolver=join_key_resolver,
            renamer=renamer,
            logger=logger,
            field_alias_resolver=field_alias_resolver,
            drop_system_columns=drop_system_columns,
            log_message="Renamed enricher columns to qualified format",
            log_field_name="enricher",
            dedup_keys=[enricher.primary_join_key],
        )
    )
    return PreparedEnricherJoinContext(
        enricher_pipeline=enricher.pipeline,
        metadata=metadata,
        merged_df=prepared_merged_df,
        enricher_df=prepared_enricher_df,
        required=enricher.required,
    )


def execute_prepared_enricher_join(
    *,
    prepared_context: PreparedEnricherJoinContext,
    conflict_resolver: ConflictResolverService,
    join_executor: Callable[..., pl.DataFrame],
    deduplicator: EnricherDeduplicatorService | None = None,
    output_how: JoinHow | None = None,
) -> pl.DataFrame:
    """Join on one key, or retry unmatched seed rows on later keys (#12004)."""
    resolved_merged_df, resolved_enricher_df = (
        conflict_resolver.detect_and_resolve_conflicts(
            prepared_context.merged_df,
            prepared_context.enricher_df,
            prepared_context.metadata.join_key_set,
        )
    )
    key_pairs = _fallback_key_pairs(prepared_context.metadata)
    if len(key_pairs) > 1:
        return execute_fallback_enricher_join(
            left_df=resolved_merged_df,
            right_df=resolved_enricher_df,
            key_pairs=key_pairs,
            pipeline_name=prepared_context.enricher_pipeline,
            required=prepared_context.required,
            output_how=output_how,
            join_executor=join_executor,
            deduplicator=deduplicator,
        )
    return join_executor(
        resolved_merged_df,
        resolved_enricher_df,
        prepared_context.metadata.seed_join_key,
        prepared_context.metadata.enricher_join_key,
        prepared_context.enricher_pipeline,
        required=prepared_context.required,
    )


def _fallback_key_pairs(
    metadata: EnricherJoinMetadataContext,
) -> tuple[tuple[str, str], ...]:
    """Return the primary key first, then the remaining fallback pairs."""
    key_pairs = getattr(metadata, "key_pairs", ())
    if not isinstance(key_pairs, tuple) or not key_pairs:
        return ()
    primary = (metadata.seed_join_key, metadata.enricher_join_key)
    ordered = [primary]
    ordered.extend(pair for pair in key_pairs if pair != primary)
    return tuple(ordered)
