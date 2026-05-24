"""Public registry-oriented composition API with lazy exports."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_PUBLIC_EXPORTS = {
    "PipelineDefinition": (
        "bioetl.composition.registry",
        "PipelineDefinition",
    ),
    "PipelineRegistry": (
        "bioetl.composition.registry",
        "PipelineRegistry",
    ),
    "create_registry": (
        "bioetl.composition.registry",
        "create_registry",
    ),
    "get_default_registry": (
        "bioetl.composition.registry_default",
        "get_default_registry",
    ),
    "register_all_pipelines": (
        "bioetl.composition.factories.pipeline.registry",
        "register_all_pipelines",
    ),
}

__all__ = list(_PUBLIC_EXPORTS)


def __getattr__(name: str) -> object:
    export = _PUBLIC_EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = export
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
