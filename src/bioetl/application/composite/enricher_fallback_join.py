"""Multi-key enricher fallback that honors the configured merge strategy."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

import polars as pl

from bioetl.application.composite.join_execution import (
    JoinCardinalityError,
    JoinHow,
    RequiredJoinKeyError,
)

if TYPE_CHECKING:
    from bioetl.application.composite.deduplication import EnricherDeduplicatorService

_SEED_ROW_ID = "__bioetl_seed_row_id"
_MATCH_MARKER = "__bioetl_join_matched"
_PROBE_HOW: JoinHow = "left"


def execute_fallback_enricher_join(
    *,
    left_df: pl.DataFrame,
    right_df: pl.DataFrame,
    key_pairs: tuple[tuple[str, str], ...],
    pipeline_name: str,
    required: bool,
    output_how: JoinHow | None,
    join_executor: Callable[..., pl.DataFrame],
    deduplicator: EnricherDeduplicatorService | None,
) -> pl.DataFrame:
    """Probe unmatched seed rows from the left, then apply ``output_how``."""
    strategy = output_how or "left"
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
    _raise_if_required_incomplete(
        pipeline_name=pipeline_name,
        required=required,
        pending_height=pending.height,
        usable_keys=usable_keys,
    )
    if not matched_frames:
        return _frame_without_matches(
            left_df=left_df,
            right_df=right_df,
            key_pairs=key_pairs,
            strategy=strategy,
            usable_keys=usable_keys,
        )
    return _assemble_fallback_frames(
        left_df=left_df,
        right_df=right_df,
        pending=pending,
        matched_frames=matched_frames,
        key_pairs=key_pairs,
        pipeline_name=pipeline_name,
        strategy=strategy,
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
    """Probe one key with a left join so later keys can still see misses."""
    if pending.height == 0:
        return None
    if left_key not in pending.columns or right_key not in right_df.columns:
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
        join_how=_PROBE_HOW,
    )
    if _MATCH_MARKER not in joined.columns:
        return None
    matched = joined.filter(pl.col(_MATCH_MARKER).fill_null(False))
    remainder = joined.filter(~pl.col(_MATCH_MARKER).fill_null(False)).select(
        original_columns
    )
    return matched, remainder


def _dedupe_fallback_frame(
    *,
    right_df: pl.DataFrame,
    right_key: str,
    pipeline_name: str,
    deduplicator: EnricherDeduplicatorService | None,
) -> pl.DataFrame:
    if deduplicator is None:
        return right_df
    return deduplicator.deduplicate(
        enricher_df=right_df,
        join_keys=[right_key],
        enricher_name=pipeline_name,
    )


def _raise_if_required_incomplete(
    *,
    pipeline_name: str,
    required: bool,
    pending_height: int,
    usable_keys: bool,
) -> None:
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


def _frame_without_matches(
    *,
    left_df: pl.DataFrame,
    right_df: pl.DataFrame,
    key_pairs: tuple[tuple[str, str], ...],
    strategy: JoinHow,
    usable_keys: bool,
) -> pl.DataFrame:
    """Keep the enricher schema when no seed row matches."""
    if not usable_keys:
        return left_df
    widened = _with_right_columns(left_df, right_df)
    if strategy == "inner":
        return widened.head(0)
    if strategy != "full":
        return widened
    return _concat_frames(
        [widened, _unmatched_right_rows(left_df, right_df, key_pairs)]
    )


def _assemble_fallback_frames(
    *,
    left_df: pl.DataFrame,
    right_df: pl.DataFrame,
    pending: pl.DataFrame,
    matched_frames: list[pl.DataFrame],
    key_pairs: tuple[tuple[str, str], ...],
    pipeline_name: str,
    strategy: JoinHow,
) -> pl.DataFrame:
    """Apply left, inner, or full output after the left-side probes."""
    frames = list(matched_frames)
    if strategy != "inner" and pending.height:
        frames.append(pending)
    if strategy == "full":
        extra = _unmatched_right_rows(left_df, right_df, key_pairs)
        if extra.height:
            frames.append(extra)
    result = _concat_frames(frames)
    drop_columns = [
        column for column in (_SEED_ROW_ID, _MATCH_MARKER) if column in result.columns
    ]
    if drop_columns:
        result = result.drop(drop_columns)
    if strategy == "left" and result.height != left_df.height:
        raise JoinCardinalityError(
            f"Join for {pipeline_name} changed cardinality "
            f"from {left_df.height} to {result.height}"
        )
    return result


def _with_right_columns(left_df: pl.DataFrame, right_df: pl.DataFrame) -> pl.DataFrame:
    """Add absent right-side columns, including join keys, as typed nulls."""
    missing = [
        pl.lit(None, dtype=right_df.schema[column]).alias(column)
        for column in right_df.columns
        if column not in left_df.columns
    ]
    if not missing:
        return left_df
    return left_df.with_columns(missing)


def _unmatched_right_rows(
    left_df: pl.DataFrame,
    right_df: pl.DataFrame,
    key_pairs: tuple[tuple[str, str], ...],
) -> pl.DataFrame:
    unmatched = right_df
    for left_key, right_key in key_pairs:
        if left_key not in left_df.columns or right_key not in unmatched.columns:
            continue
        if left_df.get_column(left_key).dtype != unmatched.get_column(right_key).dtype:
            continue
        left_values = left_df.get_column(left_key).drop_nulls()
        unmatched = unmatched.filter(~pl.col(right_key).is_in(left_values))
    return unmatched


def _concat_frames(frames: list[pl.DataFrame]) -> pl.DataFrame:
    populated = [frame for frame in frames if frame.height or len(frames) == 1]
    if len(populated) == 1:
        return populated[0]
    if _SEED_ROW_ID in populated[0].columns:
        return pl.concat(populated, how="diagonal_relaxed").sort(
            _SEED_ROW_ID,
            nulls_last=True,
        )
    return pl.concat(populated, how="diagonal_relaxed")
