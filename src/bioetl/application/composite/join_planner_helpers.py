"""Helpers for composite join planner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import polars as pl

from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.composite.deduplication import EnricherDeduplicatorService
from bioetl.application.composite.helpers.join_planner_identity import (
    extract_base_column,
    infer_pipeline_from_table,
    infer_silver_table,
    parse_pipeline_name,
    resolve_field_aliases_from_registry,
    table_path_to_name,
)
from bioetl.application.composite.protocols import JoinKeyResolverProtocol
from bioetl.domain.ports import LoggerPort

__all__ = [
    "EnricherJoinMetadataContext",
    "PrepareJoinFramesContext",
    "build_enricher_join_key_set",
    "build_enricher_join_metadata",
    "build_join_key_set",
    "count_qualified_columns",
    "extract_base_column",
    "find_missing_keys",
    "infer_pipeline_from_table",
    "infer_silver_table",
    "parse_pipeline_name",
    "prepare_join_frames",
    "prepare_qualified_right_join_dataframe",
    "resolve_field_aliases_from_registry",
    "table_path_to_name",
]


@dataclass(frozen=True, slots=True)
class EnricherJoinMetadataContext:
    """Join metadata for a single enricher pipeline."""

    join_keys_list: list[str]
    primary_key: str
    seed_join_key: str
    enricher_join_key: str
    join_key_set: set[str]


@dataclass(frozen=True, slots=True)
class PrepareJoinFramesContext:
    """Typed input bundle for qualified join-frame preparation."""

    merged_df: pl.DataFrame
    right_df: pl.DataFrame
    left_join_keys: list[str]
    right_join_keys: list[str]
    right_pipeline: str
    seed_pipeline: str | None
    deduplicator: EnricherDeduplicatorService
    join_key_resolver: JoinKeyResolverProtocol
    renamer: ColumnRenamer
    logger: LoggerPort
    field_alias_resolver: Callable[[str], dict[str, str] | None]
    drop_system_columns: Callable[[pl.DataFrame], pl.DataFrame]
    log_message: str
    log_field_name: str


def count_qualified_columns(columns: list[str]) -> int:
    """Count columns in qualified ``provider.entity.field`` format."""
    return len([col for col in columns if "." in col and not col.startswith("_")])


def build_join_key_set(
    *,
    left_join_key: str,
    right_join_key: str,
    left_join_key_qualified: str | None,
) -> set[str]:
    """Build a join-key set for symmetric or asymmetric join-key resolution."""
    join_key_set = {left_join_key, right_join_key}
    if left_join_key_qualified and left_join_key_qualified != left_join_key:
        join_key_set.add(left_join_key_qualified)
    return join_key_set


def find_missing_keys(columns: list[str], keys: list[str]) -> list[str]:
    """Return keys that are absent from the given column list."""
    return [key for key in keys if key not in columns]


def prepare_qualified_right_join_dataframe(
    *,
    source_df: pl.DataFrame,
    pipeline: str,
    join_keys: list[str],
    deduplicator: EnricherDeduplicatorService,
    join_key_resolver: JoinKeyResolverProtocol,
    renamer: ColumnRenamer,
    logger: LoggerPort,
    field_alias_resolver: Callable[[str], dict[str, str] | None],
    drop_system_columns: Callable[[pl.DataFrame], pl.DataFrame],
    log_message: str,
    log_field_name: str,
) -> pl.DataFrame:
    """Prepare a right-side join DataFrame for qualified join execution."""
    prepared_df = deduplicator.deduplicate(
        enricher_df=source_df,
        join_keys=join_keys,
        enricher_name=pipeline,
    )
    prepared_df = join_key_resolver.normalize_join_key_columns(
        prepared_df,
        join_keys,
        pipeline=None,
    )
    prepared_df = renamer.rename_dataframe(
        prepared_df,
        pipeline,
        exclude_join_keys=False,
        field_aliases=field_alias_resolver(pipeline),
    )
    logger.debug(
        log_message,
        **{
            log_field_name: pipeline,
            "qualified_count": count_qualified_columns(prepared_df.columns),
        },
    )
    return drop_system_columns(prepared_df)


def prepare_join_frames(
    request: PrepareJoinFramesContext,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Prepare left and right DataFrames for a qualified join."""
    normalized_merged = request.join_key_resolver.normalize_join_key_columns(
        request.merged_df,
        request.left_join_keys,
        pipeline=request.seed_pipeline,
    )
    prepared_right = prepare_qualified_right_join_dataframe(
        source_df=request.right_df,
        pipeline=request.right_pipeline,
        join_keys=request.right_join_keys,
        deduplicator=request.deduplicator,
        join_key_resolver=request.join_key_resolver,
        renamer=request.renamer,
        logger=request.logger,
        field_alias_resolver=request.field_alias_resolver,
        drop_system_columns=request.drop_system_columns,
        log_message=request.log_message,
        log_field_name=request.log_field_name,
    )
    return normalized_merged, prepared_right


def build_enricher_join_key_set(
    *,
    primary_key: str,
    seed_pipeline: str | None,
    enricher_pipeline: str,
    merged_columns: list[str],
    resolve_join_key_names: Callable[
        [str, str | None, str, list[str]], tuple[str, str, str | None]
    ],
) -> tuple[str, str, set[str]]:
    """Build the set of join key column names for an enricher.

    Args:
        primary_key: Primary join key field name.
        seed_pipeline: Optional seed pipeline name for qualified key resolution.
        enricher_pipeline: Enricher pipeline name.
        merged_columns: Current merged DataFrame column names.
        resolve_join_key_names: Callable that resolves join key names given
            (primary_key, seed_pipeline, enricher_pipeline, merged_columns).

    Returns:
        Tuple of (seed_join_key, enricher_join_key, join_key_set).
    """
    seed_join_key, enricher_join_key, seed_join_key_qualified = resolve_join_key_names(
        primary_key,
        seed_pipeline,
        enricher_pipeline,
        merged_columns,
    )
    join_key_set = build_join_key_set(
        left_join_key=seed_join_key,
        right_join_key=enricher_join_key,
        left_join_key_qualified=seed_join_key_qualified,
    )
    return seed_join_key, enricher_join_key, join_key_set


def build_enricher_join_metadata(
    *,
    join_keys: tuple[str, ...],
    primary_join_key: str,
    enricher_pipeline: str,
    seed_pipeline: str | None,
    merged_columns: list[str],
    resolve_join_key_names: Callable[
        [str, str | None, str, list[str]], tuple[str, str, str | None]
    ],
) -> EnricherJoinMetadataContext:
    """Build complete join metadata for a single enricher.

    Args:
        join_keys: Enricher join key field names.
        primary_join_key: Primary join key field name.
        enricher_pipeline: Enricher pipeline name.
        seed_pipeline: Optional seed pipeline name for qualified key resolution.
        merged_columns: Current merged DataFrame column names.
        resolve_join_key_names: Callable that resolves join key names.

    Returns:
        Populated ``EnricherJoinMetadataContext`` with all resolved key information.
    """
    join_keys_list = list(join_keys)
    seed_join_key, enricher_join_key, join_key_set = build_enricher_join_key_set(
        primary_key=primary_join_key,
        seed_pipeline=seed_pipeline,
        enricher_pipeline=enricher_pipeline,
        merged_columns=merged_columns,
        resolve_join_key_names=resolve_join_key_names,
    )
    return EnricherJoinMetadataContext(
        join_keys_list=join_keys_list,
        primary_key=primary_join_key,
        seed_join_key=seed_join_key,
        enricher_join_key=enricher_join_key,
        join_key_set=join_key_set,
    )
