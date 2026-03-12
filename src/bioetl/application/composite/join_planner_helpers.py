"""Helpers for composite join planner."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

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
    seed_join_key, enricher_join_key, seed_join_key_qualified = (
        resolve_join_key_names(
            primary_key,
            seed_pipeline,
            enricher_pipeline,
            merged_columns,
        )
    )
    join_key_set = {seed_join_key, enricher_join_key}
    if seed_join_key_qualified and seed_join_key_qualified != seed_join_key:
        join_key_set.add(seed_join_key_qualified)
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
    "count_qualified_columns",
    "extract_base_column",
    "infer_pipeline_from_table",
    "infer_silver_table",
    "parse_pipeline_name",
    "resolve_field_aliases_from_registry",
    "table_path_to_name",
]
