"""Execution helpers for enricher join preparation and execution."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

import polars as pl

from bioetl.application.composite.join_execution import (
    JoinCardinalityError,
    JoinHow,
    RequiredJoinKeyError,
)
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
) -> pl.DataFrame:
    """Execute prepared enricher join after resolving technical conflicts.

    A single join key uses that key directly. Additional keys are fallbacks:
    unmatched seed rows are retried in ``join_keys`` order (ADR-026 / #12004).
    Required enrichers fail closed. Optional left joins keep seed cardinality.
    """
    resolved_merged_df, resolved_enricher_df = (
        conflict_resolver.detect_and_resolve_conflicts(
            prepared_context.merged_df,
            prepared_context.enricher_df,
            prepared_context.metadata.join_key_set,
        )
    )
    key_pairs = _fallback_key_pairs(prepared_context.metadata)
    if len(key_pairs) > 1:
        return _execute_fallback_enricher_join(
            left_df=resolved_merged_df,
            right_df=resolved_enricher_df,
            key_pairs=key_pairs,
            pipeline_name=prepared_context.enricher_pipeline,
            required=prepared_context.required,
            join_executor=join_executor,
            deduplicator=deduplicator,
        )
    result = join_executor(
        resolved_merged_df,
        resolved_enricher_df,
        prepared_context.metadata.seed_join_key,
        prepared_context.metadata.enricher_join_key,
        prepared_context.enricher_pipeline,
        required=prepared_context.required,
    )
    _assert_seed_cardinality(
        left_height=resolved_merged_df.height,
        result_height=result.height,
        pipeline_name=prepared_context.enricher_pipeline,
        required=prepared_context.required,
    )
    return result


_SEED_ROW_ID = "__bioetl_seed_row_id"
_MATCH_MARKER = "__bioetl_join_matched"


def _fallback_key_pairs(
    metadata: EnricherJoinMetadataContext,
) -> tuple[tuple[str, str], ...]:
    """Return primary key first, then remaining fallback pairs."""
    key_pairs = getattr(metadata, "key_pairs", ())
    if not isinstance(key_pairs, tuple) or not key_pairs:
        return ()
    primary = (metadata.seed_join_key, metadata.enricher_join_key)
    ordered = [primary]
    ordered.extend(pair for pair in key_pairs if pair != primary)
    return tuple(ordered)


def _assert_seed_cardinality(
    *,
    left_height: int,
    result_height: int,
    pipeline_name: str,
    required: bool,
) -> None:
    """Keep left-join output aligned with the seed row count."""
    if result_height == left_height:
        return
    message = (
        f"Join for {pipeline_name} changed cardinality "
        f"from {left_height} to {result_height}"
    )
    if required:
        raise RequiredJoinKeyError(message)
    raise JoinCardinalityError(message)


def _execute_fallback_enricher_join(
    *,
    left_df: pl.DataFrame,
    right_df: pl.DataFrame,
    key_pairs: tuple[tuple[str, str], ...],
    pipeline_name: str,
    required: bool,
    join_executor: Callable[..., pl.DataFrame],
    deduplicator: EnricherDeduplicatorService | None,
) -> pl.DataFrame:
    """Match seed rows on the primary key, then on each fallback key."""
    row_id = _SEED_ROW_ID
    marker = _MATCH_MARKER
    working = left_df.with_columns(pl.Series(row_id, range(left_df.height)))
    pending = working
    original_columns = working.columns
    matched_frames: list[pl.DataFrame] = []
    usable_keys = False

    for left_key, right_key in key_pairs:
        if pending.height == 0:
            break
        if left_key not in pending.columns or right_key not in right_df.columns:
            continue
        usable_keys = True
        step_right = right_df
        if deduplicator is not None:
            step_right = deduplicator.deduplicate(
                enricher_df=right_df,
                join_keys=[right_key],
                enricher_name=pipeline_name,
            )
        step_right = step_right.with_columns(pl.lit(True).alias(marker))
        joined = join_executor(
            pending,
            step_right,
            left_key,
            right_key,
            pipeline_name,
            required=False,
            join_how=_optional_fallback_how(),
        )
        _assert_seed_cardinality(
            left_height=pending.height,
            result_height=joined.height,
            pipeline_name=pipeline_name,
            required=False,
        )
        if marker not in joined.columns:
            continue
        matched = joined.filter(pl.col(marker).fill_null(False))
        pending = joined.filter(~pl.col(marker).fill_null(False)).select(
            original_columns
        )
        if matched.height:
            matched_frames.append(matched)

    if required and pending.height:
        raise RequiredJoinKeyError(
            f"Required enricher {pipeline_name} left {pending.height} "
            "seed rows unmatched"
        )
    if required and not usable_keys:
        raise RequiredJoinKeyError(
            f"Required enricher {pipeline_name} has no usable join key columns"
        )
    if not matched_frames:
        return left_df

    if pending.height == 0 and len(matched_frames) == 1:
        result = matched_frames[0]
    else:
        frames: list[pl.DataFrame] = list(matched_frames)
        if pending.height:
            frames.append(pending)
        result = pl.concat(frames, how="diagonal").sort(row_id)
    drop_columns = [column for column in (row_id, marker) if column in result.columns]
    if drop_columns:
        result = result.drop(drop_columns)
    _assert_seed_cardinality(
        left_height=left_df.height,
        result_height=result.height,
        pipeline_name=pipeline_name,
        required=required,
    )
    return result


def _optional_fallback_how() -> JoinHow:
    """Fallback steps stay LEFT so a later key can still match."""
    return "left"
