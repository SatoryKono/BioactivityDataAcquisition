"""Composition-facing seams for application-core assembly.

This package groups the stable wiring APIs used by ``composition/`` while
avoiding eager imports of the entire wiring surface during package
initialization.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.core.wiring.factory import (
        BasePipeline as BasePipeline,
    )
    from bioetl.application.core.wiring.factory import (
        BatchExecutor as BatchExecutor,
    )
    from bioetl.application.core.wiring.factory import (
        CheckpointRuntimeService as CheckpointRuntimeService,
    )
    from bioetl.application.core.wiring.factory import (
        LockRuntimeService as LockRuntimeService,
    )
    from bioetl.application.core.wiring.factory import (
        PipelineRunner as PipelineRunner,
    )
    from bioetl.application.core.wiring.factory import (
        PipelineRunnerDependencies as PipelineRunnerDependencies,
    )
    from bioetl.application.core.wiring.factory import (
        PipelineService as PipelineService,
    )
    from bioetl.application.core.wiring.factory import (
        PostrunService as PostrunService,
    )
    from bioetl.application.core.wiring.factory import (
        PreflightService as PreflightService,
    )
    from bioetl.application.core.wiring.factory import (
        ShutdownSignal as ShutdownSignal,
    )
    from bioetl.application.core.wiring.registry import (
        ActivityTransformer as ActivityTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        AssayParametersTransformer as AssayParametersTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        AssayTransformer as AssayTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        CellLineTransformer as CellLineTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        CompoundRecordTransformer as CompoundRecordTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        CrossRefPublicationTransformer as CrossRefPublicationTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        GenericPipeline as GenericPipeline,
    )
    from bioetl.application.core.wiring.registry import (
        IDMappingTransformer as IDMappingTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        MoleculeTransformer as MoleculeTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        OpenAlexPublicationTransformer as OpenAlexPublicationTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        ProteinClassTransformer as ProteinClassTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        PubChemCompoundTransformer as PubChemCompoundTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        PublicationSimilarityTransformer as PublicationSimilarityTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        PublicationTermTransformer as PublicationTermTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        PublicationTransformer as PublicationTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        PubMedPublicationTransformer as PubMedPublicationTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        SemanticScholarPublicationTransformer as SemanticScholarPublicationTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        SubcellularFractionTransformer as SubcellularFractionTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        TargetComponentTransformer as TargetComponentTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        TargetProteinClassificationTransformer as TargetProteinClassificationTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        TargetTransformer as TargetTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        TissueTransformer as TissueTransformer,
    )
    from bioetl.application.core.wiring.registry import (
        UniProtProteinTransformer as UniProtProteinTransformer,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchCheckpointRecoveryService as BatchCheckpointRecoveryService,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchExecutionFSM as BatchExecutionFSM,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchExecutionLifecycleService as BatchExecutionLifecycleService,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchExecutionRunService as BatchExecutionRunService,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchExecutionStateService as BatchExecutionStateService,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchExecutorDependencies as BatchExecutorDependencies,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchExtractionLoopService as BatchExtractionLoopService,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchMemoryManagerService as BatchMemoryManagerService,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchMetricsRecorderService as BatchMetricsRecorderService,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchProcessingComponents as BatchProcessingComponents,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchProcessingService as BatchProcessingService,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchProcessingSupportService as BatchProcessingSupportService,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchProgressService as BatchProgressService,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchTracingManagerService as BatchTracingManagerService,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchTransformer as BatchTransformer,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchWriter as BatchWriter,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchWriterOptions as BatchWriterOptions,
    )
    from bioetl.application.core.wiring.runtime import (
        ContentHashPolicyByVersion as ContentHashPolicyByVersion,
    )
    from bioetl.application.core.wiring.runtime import (
        ContentHashVersionPolicy as ContentHashVersionPolicy,
    )
    from bioetl.application.core.wiring.runtime import (
        GoldFilterCallback as GoldFilterCallback,
    )
    from bioetl.application.core.wiring.runtime import (
        GoldTransformCallback as GoldTransformCallback,
    )
    from bioetl.application.core.wiring.runtime import (
        PipelineStorageProtocol as PipelineStorageProtocol,
    )
    from bioetl.application.core.wiring.runtime import (
        QuarantineRuntimeService as QuarantineRuntimeService,
    )
    from bioetl.application.core.wiring.runtime import (
        RecordNormalizationProcessor as RecordNormalizationProcessor,
    )
    from bioetl.application.core.wiring.runtime import (
        RecordProcessor as RecordProcessor,
    )
    from bioetl.application.core.wiring.runtime import (
        RecordProcessorConfig as RecordProcessorConfig,
    )
    from bioetl.application.core.wiring.runtime import (
        TransformCallback as TransformCallback,
    )
    from bioetl.application.core.wiring.transformer import (
        BaseTransformer as BaseTransformer,
    )
    from bioetl.application.core.wiring.transformer import (
        DefaultContractPolicy as DefaultContractPolicy,
    )
    from bioetl.application.core.wiring.transformer import (
        NoOpStructuralPolicy as NoOpStructuralPolicy,
    )
    from bioetl.application.core.wiring.transformer import (
        StructuralPolicyProtocol as StructuralPolicyProtocol,
    )
    from bioetl.application.core.wiring.transformer import (
        TransformerDependencyContext as TransformerDependencyContext,
    )
    from bioetl.application.core.wiring.transformer import (
        build_structural_policy as build_structural_policy,
    )

_WIRING_SUBMODULES = (
    "bioetl.application.core.wiring.factory",
    "bioetl.application.core.wiring.registry",
    "bioetl.application.core.wiring.runtime",
    "bioetl.application.core.wiring.transformer",
)


def _build_export_groups() -> dict[str, tuple[str, ...]]:
    return {
        module_name: tuple(import_module(module_name).__all__)
        for module_name in _WIRING_SUBMODULES
    }


_EXPORT_GROUPS = _build_export_groups()

_EXPORT_MODULES = {
    export_name: module_name
    for module_name, export_names in _EXPORT_GROUPS.items()
    for export_name in export_names
}

__all__ = list(_EXPORT_MODULES)


def __getattr__(name: str) -> object:
    module_name = _EXPORT_MODULES.get(name)
    if module_name is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(module_name), name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
