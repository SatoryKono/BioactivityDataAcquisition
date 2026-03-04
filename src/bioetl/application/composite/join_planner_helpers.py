"""Helpers for composite join planner."""

from __future__ import annotations

from bioetl.domain.registry.field_aliases import get_alias_map_for_provider


def resolve_field_aliases_from_registry(pipeline: str) -> dict[str, str] | None:
    """Resolve provider alias map for ``provider_entity`` pipeline names."""
    if "_" not in pipeline:
        return None
    provider, _entity = pipeline.split("_", 1)
    alias_map = get_alias_map_for_provider(provider)
    return alias_map if alias_map else None


def parse_pipeline_name(pipeline: str) -> tuple[str, str]:
    """Parse ``provider_entity`` pipeline name into tuple."""
    if "_" not in pipeline:
        raise ValueError(
            f"Pipeline name '{pipeline}' must be in format 'provider_entity'"
        )
    provider, entity = pipeline.split("_", 1)
    return provider, entity


__all__ = ["parse_pipeline_name", "resolve_field_aliases_from_registry"]
