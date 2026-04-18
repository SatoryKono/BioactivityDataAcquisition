"""Private execution helpers shared by BaseTransformer mixins."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer.errors import TransformationError
    from bioetl.application.core.base_transformer.structural_policy import (
        StructuralPolicyProtocol,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import SilverFilterConfig
    from bioetl.domain.ports import MetricsPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class TransformerExecutionOwner(Protocol):
    """Structural contract for execution helpers delegated from BaseTransformer."""

    provider: str
    entity_type: str
    _tracer: TracingPort
    _metrics: MetricsPort
    _silver_filters: SilverFilterConfig | None
    _structural_policy: StructuralPolicyProtocol

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Implement entity-specific transformation logic."""


def start_transform_span(
    owner: TransformerExecutionOwner,
    context: PipelineContext,
    index: int,
) -> object:  # Any: OpenTelemetry span type is dynamic
    """Create and enter an OpenTelemetry span for record transformation."""
    otel_tracer = owner._tracer.get_tracer("bioetl.transformer")
    span = otel_tracer.start_as_current_span(
        "transform_record",
        attributes={
            "bioetl.provider": owner.provider,
            "bioetl.entity_type": owner.entity_type,
            "bioetl.run_id": str(context.run_id),
            "bioetl.record_index": index,
        },
    )
    span.__enter__()
    return span


def handle_transformation_error(
    owner: TransformerExecutionOwner,
    error: TransformationError,
    context: PipelineContext,
    span: Any,
) -> str:
    """Log and annotate span for transformation errors."""
    error_type = "transformation_error"
    context.logger.warning(
        "transformation_skipped",
        reason=str(error),
        field=error.field,
        provider=owner.provider,
    )
    span.set_attribute("error", True)
    span.set_attribute("error.type", error_type)
    return error_type


def handle_validation_error(
    owner: TransformerExecutionOwner,
    error: ValueError,
    context: PipelineContext,
    span: Any,
) -> str:
    """Log and annotate span for validation errors."""
    error_type = "validation_error"
    context.logger.warning(
        "entity_validation_failed",
        error=str(error),
        provider=owner.provider,
    )
    span.set_attribute("error", True)
    span.set_attribute("error.type", error_type)
    return error_type


def record_metrics_and_close_span(
    owner: TransformerExecutionOwner,
    start_time: float,
    error_type: str | None,
    span: Any,
) -> None:
    """Record transform duration/error metrics and close the OTEL span."""
    duration = time.perf_counter() - start_time
    owner._metrics.observe_histogram(
        "bioetl_transform_duration_seconds",
        duration,
        labels={
            "provider": owner.provider,
            "entity_type": owner.entity_type,
        },
    )
    if error_type:
        owner._metrics.increment_counter(
            "bioetl_transform_errors_total",
            1,
            labels={
                "provider": owner.provider,
                "entity_type": owner.entity_type,
                "error_type": error_type,
            },
        )
    span.set_attribute("bioetl.duration_ms", duration * 1000)
    span.__exit__(None, None, None)
