"""Helpers for composite join planner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import polars as pl

from bioetl.application.composite.column_renamer import ColumnRenamerService
from bioetl.application.composite.deduplication import EnricherDeduplicatorService
from bioetl.application.composite.protocols import JoinKeyResolverProtocol
from bioetl.domain.ports import LoggerPort
from bioetl.domain.registry.field_aliases import get_alias_map_for_provider


def resolve_field_aliases_from_registry(pipeline: str) -> dict[str, str] | None:
    """Resolve provider alias map for ``provider_entity`` pipeline names.

    Args:
        pipeline: Pipeline name in ``provider_entity`` format (e.g., ``'chembl_activity'``).

    Returns:
        Alias mapping dict for the provider, or None if the pipeline name has no
        underscore separator or no aliases are registered for the provider.
    """
    if "_" not in pipeline:
        return None
    provider, _entity = pipeline.split("_", 1)
    alias_map = get_alias_map_for_provider(provider)
    return alias_map if alias_map else None


def parse_pipeline_name(pipeline: str) -> tuple[str, str]:
    """Parse ``provider_entity`` pipeline name into tuple.

    Args:
        pipeline: Pipeline name in ``provider_entity`` format (e.g., ``'chembl_activity'``).

    Returns:
        Two-element tuple ``(provider, entity)`` derived by splitting on the first underscore.
    """
    if "_" not in pipeline:
        raise ValueError(
            f"Pipeline name '{pipeline}' must be in format 'provider_entity'"
        )
    provider, entity = pipeline.split("_", 1)
    return provider, entity


def table_path_to_name(path: str) -> str:
    """Convert a layer-qualified table path to a storage table name."""
    normalized = path.replace("\\", "/")

    for layer in ("silver/", "gold/", "bronze/"):
        if layer in normalized:
            idx = normalized.find(layer)
            return normalized[idx + len(layer) :]

    return path


def infer_silver_table(pipeline_name: str) -> str:
    """Infer Silver table path from a ``provider_entity`` pipeline name."""
    parts = pipeline_name.split("_", 1)
    if len(parts) == 2:
        provider, entity = parts
        return f"silver/{provider}/{entity}"
    return f"silver/{pipeline_name}"


def infer_pipeline_from_table(table_path: str) -> str | None:
    """Infer ``provider_entity`` pipeline name from a layer-qualified table path."""
    normalized = table_path.replace("\\", "/")
    has_layer = any(layer in normalized for layer in ("silver/", "gold/", "bronze/"))
    if not has_layer:
        return None

    table_name = table_path_to_name(table_path)
    parts = table_name.split("/")
    if len(parts) == 2:
        return f"{parts[0]}_{parts[1]}"
    return None


def extract_base_column(column: str, prefix: str) -> str | None:
    """Extract base column name from a prefixed column reference."""
    if column.startswith(prefix):
        return column[len(prefix) :]
    return None


@dataclass(frozen=True, slots=True)
class EnricherJoinMetadataContext:
    """Join metadata for a single enricher pipeline."""

    join_keys_list: list[str]
    primary_key: str
    seed_join_key: str
    enricher_join_key: str
    join_key_set: set[str]


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
    renamer: ColumnRenamerService,
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
    *,
    merged_df: pl.DataFrame,
    right_df: pl.DataFrame,
    left_join_keys: list[str],
    right_join_keys: list[str],
    right_pipeline: str,
    seed_pipeline: str | None,
    deduplicator: EnricherDeduplicatorService,
    join_key_resolver: JoinKeyResolverProtocol,
    renamer: ColumnRenamerService,
    logger: LoggerPort,
    field_alias_resolver: Callable[[str], dict[str, str] | None],
    drop_system_columns: Callable[[pl.DataFrame], pl.DataFrame],
    log_message: str,
    log_field_name: str,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Prepare left and right DataFrames for a qualified join."""
    normalized_merged = join_key_resolver.normalize_join_key_columns(
        merged_df,
        left_join_keys,
        pipeline=seed_pipeline,
    )
    prepared_right = prepare_qualified_right_join_dataframe(
        source_df=right_df,
        pipeline=right_pipeline,
        join_keys=right_join_keys,
        deduplicator=deduplicator,
        join_key_resolver=join_key_resolver,
        renamer=renamer,
        logger=logger,
        field_alias_resolver=field_alias_resolver,
        drop_system_columns=drop_system_columns,
        log_message=log_message,
        log_field_name=log_field_name,
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


__all__ = [
    "EnricherJoinMetadataContext",
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
