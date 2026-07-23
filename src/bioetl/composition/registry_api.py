"""Public registry-oriented composition API with lazy exports."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition.lazy_exports import install_lazy_exports

_PIPELINE_REGISTRY_CORE_MODULE = "bioetl.composition.factories.pipeline.registry_core"


if TYPE_CHECKING:
    from bioetl.composition.factories.pipeline.registry import (
        register_all_pipelines as register_all_pipelines,
    )
    from bioetl.composition.factories.pipeline.registry_core import (
        PipelineDefinition as PipelineDefinition,
        PipelineRegistry as PipelineRegistry,
        create_registry as create_registry,
        get_default_registry as get_default_registry,
    )

_PUBLIC_EXPORTS = {
    "PipelineDefinition": (
        _PIPELINE_REGISTRY_CORE_MODULE,
        "PipelineDefinition",
    ),
    "PipelineRegistry": (
        _PIPELINE_REGISTRY_CORE_MODULE,
        "PipelineRegistry",
    ),
    "create_registry": (
        _PIPELINE_REGISTRY_CORE_MODULE,
        "create_registry",
    ),
    "get_default_registry": (
        _PIPELINE_REGISTRY_CORE_MODULE,
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
