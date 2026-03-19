"""Runtime manager builders for BatchExecutor.

Extracted from pipeline_builder.py to keep it within LOC limits.
"""

from __future__ import annotations

from bioetl.application.core.base import BasePipeline
from bioetl.application.core.batch_checkpoint_recovery_service import (
    BatchCheckpointRecoveryService,
)
from bioetl.application.core.batch_execution import (
    BatchExecutionLifecycleService,
    BatchExecutionRunService,
)
from bioetl.application.core.batch_executor import BatchExecutor
from bioetl.application.core.batch_memory_manager import BatchMemoryManagerService
from bioetl.application.core.batch_progress_service import BatchProgressService
from bioetl.application.core.batch_tracing import BatchTracingManagerService
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.lifecycle.checkpoint_manager import (
    CheckpointManagerService,
)
from bioetl.composition.factories.batch_id_generator import UuidBatchIdGenerator
from bioetl.composition.factories.services.common_service_wiring import resolve_tracer
from bioetl.domain.config import MemoryConfig
from bioetl.domain.ports import (
    BatchIdGeneratorPort,
    MemoryMonitorPort,
    TracingPort,
)

__all__ = ["build_runtime_managers"]


def build_runtime_managers(
    *,
    pipeline: BasePipeline,
    processor_config: RecordProcessorConfig,
    checkpoint_manager: CheckpointManagerService,
    memory_monitor: MemoryMonitorPort | None,
    memory_config: MemoryConfig | None,
    tracer: TracingPort | None,
    batch_id_factory: BatchIdGeneratorPort | None,
) -> tuple[
    BatchMemoryManagerService,
    BatchTracingManagerService,
    BatchIdGeneratorPort,
    BatchProgressService,
    BatchCheckpointRecoveryService,
    BatchExecutionRunService,
]:
    """Build runtime manager instances for BatchExecutor."""
    initial_batch_size = pipeline.config.batch_size or BatchExecutor.DEFAULT_BATCH_SIZE
    memory_manager = BatchMemoryManagerService(
        initial_batch_size=initial_batch_size,
        memory_monitor=memory_monitor,
        memory_config=memory_config,
        logger=pipeline.services.logger,
    )
    resolved_tracer = resolve_tracer(tracer)
    tracing_manager = BatchTracingManagerService(
        tracer=resolved_tracer,
        context=pipeline.context,
        config=processor_config,
        initial_batch_size=initial_batch_size,
        adaptive_sizing_enabled=memory_manager.enabled,
    )
    progress_service = BatchProgressService(
        logger=pipeline.services.logger, data_source=pipeline.services.data_source
    )
    checkpoint_recovery_service = BatchCheckpointRecoveryService(
        checkpoint_manager=checkpoint_manager, logger=pipeline.services.logger
    )
    execution_lifecycle_service = BatchExecutionLifecycleService(
        progress_service=progress_service,
        tracing_manager=tracing_manager,
        checkpoint_recovery_service=checkpoint_recovery_service,
    )
    execution_run_service = BatchExecutionRunService(
        execution_lifecycle_service=execution_lifecycle_service
    )
    return (
        memory_manager,
        tracing_manager,
        batch_id_factory or UuidBatchIdGenerator(),
        progress_service,
        checkpoint_recovery_service,
        execution_run_service,
    )
