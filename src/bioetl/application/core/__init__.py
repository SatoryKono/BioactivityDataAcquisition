"""Pipeline components and base classes.

NOTE: ADR-0005 introduces PipelineConfig, PipelineRuntimeConfig, PipelineServices
for decomposed pipeline configuration. Use BasePipeline.from_config() instead of
direct constructor.

Configuration consolidation (all in bioetl.domain.config):
- PipelineConfig: Static pipeline configuration
- RuntimeConfig/PipelineRuntimeConfig: CLI/runtime parameters
"""

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.lock_manager import LockManager
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.application.core.base import BasePipeline

# Re-exports from consolidated domain location
from bioetl.domain.config import (
    PipelineConfig,
    PipelineRuntimeConfig,
    RuntimeConfig,
)

__all__ = [
    # Base pipeline
    "BasePipeline",
    # Decomposed config (ADR-0005) - consolidated in domain.config
    "PipelineConfig",
    "PipelineRuntimeConfig",
    "RuntimeConfig",
    "PipelineServices",
    # Shutdown coordination (ADR-0005)
    "ShutdownSignal",
    "PipelineShutdownError",
    # Components
    "CheckpointManager",
    "LockManager",
    "QuarantineManager",
]
