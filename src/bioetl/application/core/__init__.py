"""Pipeline components and base classes.

NOTE: ADR-0005 introduces PipelineConfig, PipelineRuntimeConfig, PipelineServices
for decomposed pipeline configuration. Use BasePipeline.from_config() instead of
direct constructor.
"""

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.lock_manager import LockManager
from bioetl.application.core.pipeline_config import (
    PipelineRuntimeConfig,
)
from bioetl.domain.pipeline_config import PipelineConfig
from bioetl.application.core.pipeline_services import PipelineServices
from bioetl.application.core.quarantine_manager import QuarantineManager
from bioetl.application.core.shutdown import PipelineShutdownError, ShutdownSignal
from bioetl.application.core.base import BasePipeline

__all__ = [
    # Base pipeline
    "BasePipeline",
    # New decomposed config (ADR-0005)
    "PipelineConfig",
    "PipelineRuntimeConfig",
    "PipelineServices",
    # Shutdown coordination (ADR-0005)
    "ShutdownSignal",
    "PipelineShutdownError",
    # Components
    "CheckpointManager",
    "LockManager",
    "QuarantineManager",
]
