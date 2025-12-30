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
from bioetl.application.core.batch_executor import BatchExecutor
from bioetl.application.core.batch_transformer import (
    BatchTransformer,
    StreamingBatchProcessor,
    TransformedRecord,
    TransformResult,
)
from bioetl.application.core.batch_writer import BatchWriter
from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.cleanup_service import (
    CleanupPreview,
    CleanupResult,
    CleanupService,
    LayerInfo,
)
from bioetl.application.core.lifecycle_orchestrator import (
    ClearDecision,
    LifecycleOrchestrator,
)
from bioetl.application.core.lock_manager import LockManager
from bioetl.application.core.memory_monitor import (
    MemoryConfig,
    MemoryMonitor,
    MemoryStats,
)
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.postrun_service import (
    DQResult,
    PostrunService,
    VacuumResult,
)
from bioetl.application.core.preflight_service import PreflightService
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.application.core.runner import PipelineRunner
from bioetl.application.core.shutdown import (
    PipelineShutdownError,
    ShutdownReason,
    ShutdownService,
    ShutdownSignal,
    create_shutdown_service,
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
from bioetl.domain.medallion import (
    Layer,
    WriteMode,
    WriteModePolicy,
)

__all__ = [
    "BasePipeline",
    "BaseTransformer",
    "BatchExecutor",
    "BatchTransformer",
    "BatchWriter",
    "CheckpointManager",
    "CleanupPreview",
    "CleanupResult",
    "CleanupService",
    "ClearDecision",
    "DQResult",
    "Layer",
    "LayerInfo",
    "LifecycleOrchestrator",
    "LockManager",
    "MemoryConfig",
    "MemoryMonitor",
    "MemoryStats",
    "PipelineConfig",
    "PipelineExecutor",  # Deprecated: use BatchExecutor
    "PipelineRunner",
    "PipelineServices",
    "PipelineShutdownError",
    "PostrunService",
    "PreflightService",
    "QuarantineManager",
    "RecordProcessor",  # Deprecated: use BatchExecutor
    "RuntimeConfig",
    "ShutdownReason",
    "ShutdownService",
    "ShutdownSignal",
    "StreamingBatchProcessor",
    "TransformResult",
    "TransformedRecord",
    "VacuumResult",
    "WriteMode",
    "WriteModePolicy",
    "aggregate_nested_lists",
    "create_shutdown_service",
    "extract_list_field",
    "flatten_nested_dict",
    "normalize_string",
    "parse_date_field",
    "safe_extract",
    "validate_smiles",
]


# =============================================================================
# Deprecated Aliases (14-day transition period per RULES.md §7.1)
# Removal date: 2026-01-13
# =============================================================================

import warnings as _warnings
from typing import Any


def __getattr__(name: str) -> type[Any]:
    """Provide deprecated aliases with warnings."""
    if name == "PipelineExecutor":
        _warnings.warn(
            "PipelineExecutor is deprecated and will be removed on 2026-01-13. "
            "Use BatchExecutor instead, which combines extraction and processing.",
            DeprecationWarning,
            stacklevel=2,
        )
        from bioetl.application.core.executor import PipelineExecutor

        return PipelineExecutor
    if name == "RecordProcessor":
        _warnings.warn(
            "RecordProcessor is deprecated and will be removed on 2026-01-13. "
            "Use BatchExecutor instead, which combines extraction and processing.",
            DeprecationWarning,
            stacklevel=2,
        )
        from bioetl.application.core.record_processor import RecordProcessor

        return RecordProcessor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
