"""Pipeline identity and table-path helpers for composite join planning."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.registry.field_aliases import get_alias_map_for_provider

__all__ = [
    "extract_base_column",
    "infer_pipeline_from_table",
    "infer_silver_table",
    "parse_pipeline_name",
    "resolve_field_aliases_from_registry",
    "table_path_to_name",
    "try_parse_pipeline_identity",
]


@dataclass(frozen=True, slots=True)
class PipelineIdentity:
    """Parsed ``provider_entity`` identity used by helper-level resolvers."""

    provider: str
    entity: str


def try_parse_pipeline_identity(pipeline: str) -> PipelineIdentity | None:
    """Return parsed pipeline identity or ``None`` when format is invalid."""
    if "_" not in pipeline:
        return None
    provider, entity = pipeline.split("_", 1)
    return PipelineIdentity(provider=provider, entity=entity)


def resolve_field_aliases_from_registry(pipeline: str) -> dict[str, str] | None:
    """Resolve provider alias map for ``provider_entity`` pipeline names.

    Args:
        pipeline: Pipeline name in ``provider_entity`` format (e.g., ``'chembl_activity'``).

    Returns:
        Alias mapping dict for the provider, or None if the pipeline name has no
        underscore separator or no aliases are registered for the provider.
    """
    identity = try_parse_pipeline_identity(pipeline)
    if identity is None:
        return None
    alias_map = get_alias_map_for_provider(identity.provider)
    return alias_map if alias_map else None


def parse_pipeline_name(pipeline: str) -> tuple[str, str]:
    """Parse ``provider_entity`` pipeline name into tuple.

    Args:
        pipeline: Pipeline name in ``provider_entity`` format (e.g., ``'chembl_activity'``).

    Returns:
        Two-element tuple ``(provider, entity)`` derived by splitting on the first underscore.
    """
    identity = try_parse_pipeline_identity(pipeline)
    if identity is None:
        raise ValueError(
            f"Pipeline name '{pipeline}' must be in format 'provider_entity'"
        )
    return identity.provider, identity.entity


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
    identity = try_parse_pipeline_identity(pipeline_name)
    if identity is not None:
        return f"silver/{identity.provider}/{identity.entity}"
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
