"""Composition-facing seams for application-core assembly.

This package groups the stable wiring APIs used by ``composition/`` while
avoiding eager imports of the entire wiring surface during package
initialization. Static re-export declarations live in the adjacent stub.
"""

from __future__ import annotations

from importlib import import_module

from bioetl.application.core.wiring._runtime_export_names import (
    RUNTIME_EXPORT_NAMES,
)

# Static metadata-only map: avoid importing heavy wiring submodules at package load.
# `_runtime_export_names` is a pure name tuple (no service imports).
# Later groups intentionally overwrite shared names (factory -> runtime).
_EXPORT_GROUPS: dict[str, tuple[str, ...]] = {
    "bioetl.application.core.wiring.factory": (
        "BasePipeline",
        "BatchExecutor",
        "CheckpointRuntimeService",
        "LockRuntimeService",
        "PipelineRunner",
        "PipelineRunnerDependencies",
        "PipelineService",
        "PostrunService",
        "PreflightService",
        "ShutdownSignal",
    ),
    "bioetl.application.core.wiring.registry": (
        "ActivityTransformer",
        "AssayParametersTransformer",
        "AssayTransformer",
        "CellLineTransformer",
        "CompoundRecordTransformer",
        "CrossRefPublicationTransformer",
        "GenericPipeline",
        "IDMappingTransformer",
        "MoleculeTransformer",
        "OpenAlexPublicationTransformer",
        "ProteinClassTransformer",
        "PubChemCompoundTransformer",
        "PubMedPublicationTransformer",
        "PublicationSimilarityTransformer",
        "PublicationTermTransformer",
        "PublicationTransformer",
        "SemanticScholarPublicationTransformer",
        "SubcellularFractionTransformer",
        "TargetComponentTransformer",
        "TargetProteinClassificationTransformer",
        "TargetTransformer",
        "TissueTransformer",
        "UniProtProteinTransformer",
    ),
    "bioetl.application.core.wiring.runtime": RUNTIME_EXPORT_NAMES,
    "bioetl.application.core.wiring.transformer": (
        "BaseTransformer",
        "DefaultContractPolicy",
        "NoOpStructuralPolicy",
        "StructuralPolicyProtocol",
        "TransformerDependencyContext",
        "build_structural_policy",
    ),
}

_EXPORT_MODULES = {
    export_name: module_name
    for module_name, export_names in _EXPORT_GROUPS.items()
    for export_name in export_names
}
__all__ = [*_EXPORT_MODULES]


def __getattr__(name: str) -> object:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
