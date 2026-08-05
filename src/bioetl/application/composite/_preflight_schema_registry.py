"""Schema registry discovery for composite preflight validation."""

from __future__ import annotations

from importlib import import_module

__all__ = ["find_schema_class", "load_schema_registry"]


def find_schema_class(module: object) -> type | None:
    """Return the first exported generated schema class from a module."""
    for exported in getattr(module, "__all__", ()):
        candidate = (
            getattr(module, exported, None) if isinstance(exported, str) else exported
        )
        if isinstance(candidate, type) and hasattr(candidate, "to_schema"):
            return candidate

    for candidate in vars(module).values():
        if isinstance(candidate, type) and hasattr(candidate, "to_schema"):
            return candidate
    return None


def load_schema_registry() -> dict[str, type]:
    """Build schema registry keyed by ``provider_entity``."""
    module_aliases: dict[tuple[str, str], str] = {
        ("chembl", "protein_class"): "protein_classification",
    }
    registry: dict[str, type] = {}

    from bioetl.domain.schemas.generated.registry import CANONICAL_SCHEMA_REGISTRY

    for entry in CANONICAL_SCHEMA_REGISTRY:
        provider = entry.provider.lower()
        entity = entry.entity.lower()
        module_entity = module_aliases.get((provider, entity), entity)
        module_name = f"bioetl.domain.schemas.{provider}.{module_entity}"
        pipeline_key = f"{provider}_{entity}"

        try:
            module = import_module(module_name)
        except ImportError:
            continue

        schema_class = find_schema_class(module)
        if schema_class is not None:
            registry[pipeline_key] = schema_class

    return registry
