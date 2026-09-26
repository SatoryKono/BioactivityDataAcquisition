"""Typed request objects for batch-executor assembly."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.application.core.wiring.runtime import (
    BatchProcessingComponents,
    CheckpointRuntimeService,
)
from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext

if TYPE_CHECKING:
    import pyarrow as pa

    from bioetl.application.core.wiring.runtime import BasePipeline, ShutdownSignal
    from bioetl.application.observability.domain_event_emitter import (
        DomainEventEmitterProtocol,
    )
    from bioetl.domain.config import MemoryConfig
    from bioetl.domain.ports import (
        BatchIdGeneratorPort,
        MemoryMonitorPort,
        TracingPort,
    )
    from bioetl.domain.types import GoldSchemaType


BatchProcessingComponentsFactory = Callable[..., BatchProcessingComponents]


@dataclass(frozen=True, slots=True)
class BatchExecutorBuildRequest:
    """Canonical input bundle for batch-executor construction."""

    pipeline: BasePipeline
    callbacks: PipelineCallbacksContext
    silver_schema: pa.Schema | None
    gold_schema: GoldSchemaType
    checkpoint_manager: CheckpointRuntimeService
    shutdown_signal: ShutdownSignal
    create_batch_processing_components_fn: BatchProcessingComponentsFactory
    strict_gold_validation: bool = True
    lock_validator: Callable[[], Awaitable[bool]] | None = None
    tracer: TracingPort | None = None
    memory_monitor: MemoryMonitorPort | None = None
    memory_config: MemoryConfig | None = None
    bronze_output_path: str | None = None
    silver_output_path: str | None = None
    gold_output_path: str | None = None
    flat_structure: bool = False
    batch_id_factory: BatchIdGeneratorPort | None = None
    domain_event_emitter: DomainEventEmitterProtocol | None = None
