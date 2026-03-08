"""Helpers for assembling batch processing services in composition layer."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from bioetl.application.core.batch_processing_service import BatchProcessingService
from bioetl.application.core.batch_tracing import BatchTracingManagerService
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.protocols import GoldFilterCallback
from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.infrastructure.validation import PanderaGoldValidator

if TYPE_CHECKING:
    from bioetl.application.core.base import BasePipeline
    from bioetl.domain.ports import BatchIdGeneratorPort, TracingPort

    from .services_factory_pipeline_builder import BatchProcessingComponents


def build_components_and_processing_service(
    *,
    pipeline: BasePipeline,
    processor_config: RecordProcessorConfig,
    error_classifier: ErrorClassifier,
    callbacks: PipelineCallbacksContext,
    gold_filter: GoldFilterCallback,
    gold_validator: PanderaGoldValidator,
    tracer: TracingPort | None,
    lock_validator: Callable[[], Awaitable[bool]] | None,
    tracing_manager: BatchTracingManagerService,
    batch_id_factory: BatchIdGeneratorPort,
    create_batch_processing_components_fn: Callable[..., BatchProcessingComponents],
) -> tuple[BatchProcessingComponents, BatchProcessingService]:
    """Build component stack and BatchProcessingService.

    Args:
        pipeline: Configured pipeline instance providing services and context.
        processor_config: Record processor configuration (table names, schemas, keys).
        error_classifier: Classifier for categorizing processing errors.
        callbacks: Pipeline transformation callbacks (transform, gold_filter, gold_transform).
        gold_filter: Predicate determining if a Silver record writes to Gold.
        gold_validator: Pandera validator applied to Gold-layer DataFrames.
        tracer: Optional TracingPort for distributed tracing.
        lock_validator: Optional async callable for lock validation before writes.
        tracing_manager: Batch-level tracing manager for span lifecycle.
        batch_id_factory: Generator for unique batch identifiers.
        create_batch_processing_components_fn: Injectable callable for creating
            BatchProcessingComponents (allows test substitution).

    Returns:
        Tuple of (BatchProcessingComponents, BatchProcessingService).
    """
    components = create_batch_processing_components_fn(
        services=pipeline.services,
        context=pipeline.context,
        config=processor_config,
        error_classifier=error_classifier,
        transform_callback=callbacks.transform,
        gold_filter_callback=gold_filter,
        gold_transform_callback=callbacks.gold_transform,
        gold_validator=gold_validator,
        tracer=tracer,
        lock_validator=lock_validator,
    )
    batch_processing_service = BatchProcessingService(
        services=pipeline.services,
        context=pipeline.context,
        config=processor_config,
        logger=pipeline.services.logger,
        batch_metrics=components.batch_metrics,
        transformer=components.transformer,
        writer=components.writer,
        tracing_manager=tracing_manager,
        batch_id_factory=batch_id_factory,
    )
    return components, batch_processing_service
