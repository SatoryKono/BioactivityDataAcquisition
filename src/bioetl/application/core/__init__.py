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
from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.cleanup_service import (
    CleanupPreview,
    CleanupResult,
    CleanupService,
    LayerInfo,
)
from bioetl.application.core.lock_manager import LockManager
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.application.core.transform_utils import (
    aggregate_nested_lists,
    extract_list_field,
    flatten_nested_dict,
    normalize_string,
    parse_date_field,
    safe_extract,
    validate_smiles,
)

# Re-exports from consolidated domain location
from bioetl.domain.config import PipelineConfig, RuntimeConfig

__all__ = [
    # Base classes
    "BasePipeline",
    "BaseTransformer",
    # Components
    "CheckpointManager",
    "CleanupPreview",
    "CleanupResult",
    "CleanupService",
    "LayerInfo",
    "LockManager",
    # Decomposed config (ADR-0005) - consolidated in domain.config
    "PipelineConfig",
    "PipelineServices",
    "PipelineShutdownError",
    "QuarantineManager",
    "RuntimeConfig",
    # Shutdown coordination (ADR-0005)
    "ShutdownSignal",
    # Transform utilities
    "aggregate_nested_lists",
    "extract_list_field",
    "flatten_nested_dict",
    "normalize_string",
    "parse_date_field",
    "safe_extract",
    "validate_smiles",
]
