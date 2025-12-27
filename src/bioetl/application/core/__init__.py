"""Pipeline components and base classes.

NOTE: ADR-0005 introduces PipelineConfig, RuntimeConfig, PipelineServices
for decomposed pipeline configuration. Use BasePipeline.from_config() instead of
direct constructor.

Configuration consolidation (all in bioetl.domain.config):
- PipelineConfig: Static pipeline configuration
- RuntimeConfig: CLI/runtime parameters
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.application.core.batch_transformer import (
    BatchTransformer,
    StreamingBatchProcessor,
    TransformedRecord,
    TransformResult,
)
from bioetl.application.core.batch_writer import BatchWriter
from bioetl.application.core.memory_monitor import (
    MemoryConfig,
    MemoryMonitor,
    MemoryStats,
)
from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.cleanup_service import (
    CleanupPreview,
    CleanupResult,
    CleanupService,
    LayerInfo,
)
from bioetl.application.core.health_aggregator import HealthAggregator
from bioetl.application.core.lifecycle_orchestrator import (
    ClearDecision,
    LifecycleOrchestrator,
)
from bioetl.application.core.lock_manager import LockManager
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.postrun_service import (
    DQResult,
    PostrunService,
    VacuumResult,
)
from bioetl.application.core.preflight_service import PreflightService
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.application.core.medallion_policy import (
    Layer,
    WriteModePolicy,
    WriteMode,
)
from bioetl.application.core.transform_utils import (
    aggregate_nested_lists,
    extract_list_field,
    flatten_nested_dict,
    normalize_string,
    parse_date_field,
    safe_extract,
    validate_smiles,
)
from bioetl.domain.config import PipelineConfig, RuntimeConfig

__all__ = [
    "BasePipeline",
    "BaseTransformer",
    "BatchTransformer",
    "BatchWriter",
    "CheckpointManager",
    "CleanupPreview",
    "CleanupResult",
    "CleanupService",
    "ClearDecision",
    "DQResult",
    "HealthAggregator",
    "Layer",
    "LayerInfo",
    "LifecycleOrchestrator",
    "LockManager",
    "MemoryConfig",
    "MemoryMonitor",
    "MemoryStats",
    "WriteModePolicy",
    "PipelineConfig",
    "PipelineServices",
    "PipelineShutdownError",
    "PostrunService",
    "PreflightService",
    "QuarantineManager",
    "RuntimeConfig",
    "ShutdownSignal",
    "StreamingBatchProcessor",
    "TransformedRecord",
    "TransformResult",
    "VacuumResult",
    "WriteMode",
    "aggregate_nested_lists",
    "extract_list_field",
    "flatten_nested_dict",
    "normalize_string",
    "parse_date_field",
    "safe_extract",
    "validate_smiles",
]
