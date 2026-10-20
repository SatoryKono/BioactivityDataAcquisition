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
    pending = left_df.with_columns(pl.Series(_SEED_ROW_ID, range(left_df.height)))
    original_columns = pending.columns
    matched_frames: list[pl.DataFrame] = []
    usable_keys = False
    for left_key, right_key in key_pairs:
        step = _join_fallback_key(
            pending=pending,
            right_df=right_df,
            left_key=left_key,
            right_key=right_key,
            pipeline_name=pipeline_name,
            original_columns=original_columns,
            join_executor=join_executor,
            deduplicator=deduplicator,
        )
        if step is None:
            continue
        usable_keys = True
        matched, pending = step
        if matched.height:
            matched_frames.append(matched)
    _raise_if_required_fallback_incomplete(
        pipeline_name=pipeline_name,
        required=required,
        pending_height=pending.height,
        usable_keys=usable_keys,
    )
    if not matched_frames:
        return left_df
    return _assemble_fallback_frames(
        left_df=left_df,
        pending=pending,
        matched_frames=matched_frames,
        pipeline_name=pipeline_name,
        required=required,
    )


def _join_fallback_key(
    *,
    pending: pl.DataFrame,
    right_df: pl.DataFrame,
    left_key: str,
    right_key: str,
    pipeline_name: str,
    original_columns: list[str],
    join_executor: Callable[..., pl.DataFrame],
    deduplicator: EnricherDeduplicatorService | None,
) -> tuple[pl.DataFrame, pl.DataFrame] | None:
    """Join one fallback key and split matched rows from the remainder."""
    if not _fallback_key_is_usable(
        pending=pending,
        right_df=right_df,
        left_key=left_key,
        right_key=right_key,
    ):
        return None
    step_right = _dedupe_fallback_frame(
        right_df=right_df,
        right_key=right_key,
        pipeline_name=pipeline_name,
        deduplicator=deduplicator,
    ).with_columns(pl.lit(True).alias(_MATCH_MARKER))
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
    if _MATCH_MARKER not in joined.columns:
        return None
    matched = joined.filter(pl.col(_MATCH_MARKER).fill_null(False))
    remainder = joined.filter(~pl.col(_MATCH_MARKER).fill_null(False)).select(
        original_columns
    )
    return matched, remainder


def _fallback_key_is_usable(
    *,
    pending: pl.DataFrame,
    right_df: pl.DataFrame,
    left_key: str,
    right_key: str,
) -> bool:
    """Return whether this fallback key can be joined."""
    if pending.height == 0:
        return False
    return left_key in pending.columns and right_key in right_df.columns


def _dedupe_fallback_frame(
    *,
    right_df: pl.DataFrame,
    right_key: str,
    pipeline_name: str,
    deduplicator: EnricherDeduplicatorService | None,
) -> pl.DataFrame:
    """Collapse duplicate right rows on the key used for this fallback step."""
    if deduplicator is None:
        return right_df
    return deduplicator.deduplicate(
        enricher_df=right_df,
        join_keys=[right_key],
        enricher_name=pipeline_name,
    )


def _raise_if_required_fallback_incomplete(
    *,
    pipeline_name: str,
    required: bool,
    pending_height: int,
    usable_keys: bool,
) -> None:
    """Fail a required enricher that left seed rows unmatched."""
    if not required:
        return
    if pending_height:
        raise RequiredJoinKeyError(
            f"Required enricher {pipeline_name} left {pending_height} "
            "seed rows unmatched"
        )
    if not usable_keys:
        raise RequiredJoinKeyError(
            f"Required enricher {pipeline_name} has no usable join key columns"
        )


def _assemble_fallback_frames(
    *,
    left_df: pl.DataFrame,
    pending: pl.DataFrame,
    matched_frames: list[pl.DataFrame],
    pipeline_name: str,
    required: bool,
) -> pl.DataFrame:
    """Restore seed order and drop fallback bookkeeping columns."""
    result = _concat_fallback_frames(pending=pending, matched_frames=matched_frames)
    drop_columns = [
        column for column in (_SEED_ROW_ID, _MATCH_MARKER) if column in result.columns
    ]
    if drop_columns:
        result = result.drop(drop_columns)
    _assert_seed_cardinality(
        left_height=left_df.height,
        result_height=result.height,
        pipeline_name=pipeline_name,
        required=required,
    )
    return result


def _concat_fallback_frames(
    *,
    pending: pl.DataFrame,
    matched_frames: list[pl.DataFrame],
) -> pl.DataFrame:
    """Combine matched fallback frames with any still-unmatched seed rows."""
    if pending.height == 0 and len(matched_frames) == 1:
        return matched_frames[0]
    frames = list(matched_frames)
    if pending.height:
        frames.append(pending)
    return pl.concat(frames, how="diagonal").sort(_SEED_ROW_ID)


def _optional_fallback_how() -> JoinHow:
    """Fallback steps stay LEFT so a later key can still match."""
    return "left"
