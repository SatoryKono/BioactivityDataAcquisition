"""Construction helpers for the lazy domain-port compatibility facade."""

from __future__ import annotations

from . import entity_type as _entity_type
from . import pipeline_callbacks as _pipeline_callbacks
from . import source_config as _source_config


def build_export_modules(
    export_groups: dict[str, tuple[str, ...]],
) -> dict[str, str]:
    """Map export names to modules with fail-fast collision detection."""
    export_modules: dict[str, str] = {}
    for module_name, export_names in export_groups.items():
        for export_name in export_names:
            existing = export_modules.get(export_name)
            if existing is not None and existing != module_name:
                raise RuntimeError(
                    f"duplicate ports export {export_name!r}: "
                    f"{existing!r} and {module_name!r}"
                )
            export_modules[export_name] = module_name
    _ = (
        _entity_type.__name__,
        _pipeline_callbacks.__name__,
        _source_config.__name__,
    )
    return export_modules


__all__ = ["build_export_modules"]
