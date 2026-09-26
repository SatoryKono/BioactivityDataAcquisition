"""Delta writer path-layout policy (#11241)."""

from __future__ import annotations

from pathlib import Path


def has_provider_entity_suffix(
    path: Path,
    *,
    provider: str,
    entity_type: str,
) -> bool:
    """Return True when a path already ends with provider/entity segments."""
    parts = Path(str(path).replace("\\", "/")).parts
    if len(parts) < 2:
        return False
    return parts[-2:] == (provider, entity_type)


def resolve_delta_writer_base_path(
    resolved_path: Path,
    *,
    provider: str,
    entity_type: str,
    flat_structure: bool,
) -> Path:
    """Normalize Delta writer base_path to the layer root when path is entity-scoped."""
    runtime_path = Path(str(resolved_path).replace("\\", "/"))
    if flat_structure:
        return runtime_path
    if has_provider_entity_suffix(
        runtime_path,
        provider=provider,
        entity_type=entity_type,
    ):
        return runtime_path.parent.parent
    return runtime_path
