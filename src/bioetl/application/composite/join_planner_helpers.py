"""Helpers for composite join planner."""

from __future__ import annotations

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


__all__ = [
    "extract_base_column",
    "infer_pipeline_from_table",
    "infer_silver_table",
    "parse_pipeline_name",
    "resolve_field_aliases_from_registry",
    "table_path_to_name",
]
