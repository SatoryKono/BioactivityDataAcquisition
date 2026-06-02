"""Public registry-oriented composition API with lazy exports."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition._lazy_exports import install_lazy_exports

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
        "bioetl.composition.registry",
        "get_default_registry",
    ),
    "register_all_pipelines": (
        "bioetl.composition.factories.pipeline.registry",
        "register_all_pipelines",
    ),
}

__all__ = list(_PUBLIC_EXPORTS)
install_lazy_exports(
    module_globals=globals(),
    public_exports=_PUBLIC_EXPORTS,
    module_name=__name__,
    explicit_exports=__all__,
    cache=True,
)
