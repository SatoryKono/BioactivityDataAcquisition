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


__all__ = [
    "parse_pipeline_name",
    "resolve_field_aliases_from_registry",
    "table_path_to_name",
]
