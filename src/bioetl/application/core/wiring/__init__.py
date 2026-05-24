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
        BasePipeline,
        BatchExecutor,
        CheckpointRuntimeService,
        LockRuntimeService,
        PipelineRunner,
        PipelineRunnerDependencies,
        PipelineService,
        PostrunService,
        PreflightService,
        ShutdownSignal,
    )
    from bioetl.application.core.wiring.registry import (
        ActivityTransformer,
        AssayParametersTransformer,
        AssayTransformer,
        CellLineTransformer,
        CompoundRecordTransformer,
        CrossRefPublicationTransformer,
        GenericPipeline,
        IDMappingTransformer,
        MoleculeTransformer,
        OpenAlexPublicationTransformer,
        ProteinClassTransformer,
        PubChemCompoundTransformer,
        PublicationSimilarityTransformer,
        PublicationTermTransformer,
        PublicationTransformer,
        PubMedPublicationTransformer,
        SemanticScholarPublicationTransformer,
        SubcellularFractionTransformer,
        TargetComponentTransformer,
        TargetTransformer,
        TissueTransformer,
        UniProtProteinTransformer,
    )
    from bioetl.application.core.wiring.runtime import (
        BatchCheckpointRecoveryService,
        BatchExecutionFSM,
        BatchExecutionLifecycleService,
        BatchExecutionRunService,
        BatchExecutionStateService,
        BatchExecutorDependencies,
        BatchExtractionLoopService,
        BatchMemoryManagerService,
        BatchMetricsRecorderService,
        BatchProcessingComponents,
        BatchProcessingService,
        BatchProcessingSupportService,
        BatchProgressService,
        BatchTracingManagerService,
        BatchTransformer,
        BatchWriter,
        BatchWriterOptions,
        ContentHashPolicyByVersion,
        ContentHashVersionPolicy,
        GoldFilterCallback,
        GoldTransformCallback,
        PipelineStorageProtocol,
        QuarantineRuntimeService,
        RecordNormalizationProcessor,
        RecordProcessor,
        RecordProcessorConfig,
        TransformCallback,
    )
    from bioetl.application.core.wiring.transformer import (
        BaseTransformer,
        DefaultContractPolicy,
        NoOpStructuralPolicy,
        StructuralPolicyProtocol,
        TransformerDependencyContext,
        build_structural_policy,
    )

_EXPORT_GROUPS = {
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
        "TargetTransformer",
        "TissueTransformer",
        "UniProtProteinTransformer",
    ),
    "bioetl.application.core.wiring.runtime": (
        "BatchCheckpointRecoveryService",
        "BatchExecutionFSM",
        "BatchExecutionLifecycleService",
        "BatchExecutionRunService",
        "BatchExecutionStateService",
        "BatchExecutorDependencies",
        "BatchExtractionLoopService",
        "BatchMemoryManagerService",
        "BatchMetricsRecorderService",
        "BatchProcessingComponents",
        "BatchProcessingService",
        "BatchProcessingSupportService",
        "BatchProgressService",
        "BatchTracingManagerService",
        "BatchTransformer",
        "BatchWriter",
        "BatchWriterOptions",
        "ContentHashPolicyByVersion",
        "ContentHashVersionPolicy",
        "GoldFilterCallback",
        "GoldTransformCallback",
        "PipelineStorageProtocol",
        "QuarantineRuntimeService",
        "RecordNormalizationProcessor",
        "RecordProcessor",
        "RecordProcessorConfig",
        "TransformCallback",
    ),
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
