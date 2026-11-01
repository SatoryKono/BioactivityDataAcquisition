"""Private execution helpers shared by BaseTransformer mixins."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Protocol, cast

from bioetl.application.core.pipeline_span_lifecycle import (
    _ClosableSpan as _ClosableSpan,
)

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer.errors import TransformationError
    from bioetl.application.core.base_transformer.structural_policy import (
        StructuralPolicyProtocol,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import FilterDecision, SilverFilterConfig
    from bioetl.domain.ports import MetricsPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord

_STRUCTURAL_ACTION_BY_REASON_CODE: dict[str, str] = {
    "required_field_missing": "presence_quarantine",
    "structural_policy_type_mismatch": "required_type_quarantine",
    "structural_policy_null_optional_forbidden": "optional_nonnullable_quarantine",
}
_STRUCTURAL_ACTION_BY_EVENT: dict[str, str] = {
    "silver_structural_type_coerced_to_null": "nullable_type_to_null",
}


def classify_structural_action(
    details: dict[str, object] | None,
    event_names: set[str],
) -> str | None:
    """Map structural details/events to a bounded telemetry action label."""
    if details is not None:
        reason_code = details.get("reason_code")
        if isinstance(reason_code, str):
            mapped = _STRUCTURAL_ACTION_BY_REASON_CODE.get(reason_code)
            if mapped is not None:
                return mapped
    for event_name in event_names:
        mapped = _STRUCTURAL_ACTION_BY_EVENT.get(event_name)
        if mapped is not None:
            return mapped
    return None


def classify_structural_shadow_comparison(
    *,
    structural_rejected: bool,
    silver_filter_decision: FilterDecision | None,
) -> str | None:
    """Build a bounded comparison label for structural vs Silver filtering."""
    if silver_filter_decision is None:
        return None
    silver_state = "reject" if not silver_filter_decision.include else "pass"
    structural_state = "reject" if structural_rejected else "pass"
    return f"structural_{structural_state}_silver_filter_{silver_state}"


def optional_sources_for_field(
    policy: object,
    field_name: str | None,
) -> list[str]:
    """Return resolved optionality metadata for one policy field."""
    if not field_name:
        return []
    for contract in getattr(policy, "contracts", ()):
        if getattr(contract, "field_name", None) == field_name:
            return list(getattr(contract, "optional_sources", ()))
    return []


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
        ...

    def _start_transform_span(
        self,
        context: PipelineContext,
        index: int,
    ) -> _ClosableSpan:
        """Create and enter an OpenTelemetry span for record transformation."""
        ...

    def _apply_structural_policy(
        self,
        context: PipelineContext,
        result: SilverRecord | None,
        index: int,
    ) -> SilverRecord | None:
        """Apply schema-aware structural policy before structural Silver filters."""
        ...

    def _handle_transformation_error(
        self,
        error: TransformationError,
        context: PipelineContext,
        span: _ClosableSpan,
    ) -> str:
        """Log and annotate span for transformation errors."""
        ...

    def _handle_validation_error(
        self,
        error: ValueError,
        context: PipelineContext,
        span: _ClosableSpan,
    ) -> str:
        """Log and annotate span for validation errors."""
        ...

    def _record_metrics_and_close_span(
        self,
        start_time: float,
        error_type: str | None,
        span: _ClosableSpan,
    ) -> None:
        """Record transform duration/error metrics and close the OTEL span."""
        ...


def start_transform_span(
    owner: TransformerExecutionOwner,
    context: PipelineContext,
    index: int,
) -> _ClosableSpan:
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
    closable_span = cast(_ClosableSpan, cast(object, span))
    closable_span.__enter__()
    return closable_span


def handle_transformation_error(
    owner: TransformerExecutionOwner,
    error: TransformationError,
    context: PipelineContext,
    span: _ClosableSpan,
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
    span: _ClosableSpan,
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
    span: _ClosableSpan,
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
