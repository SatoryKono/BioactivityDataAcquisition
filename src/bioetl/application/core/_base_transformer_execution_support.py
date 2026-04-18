"""Private execution helpers shared by BaseTransformer mixins."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Protocol, cast

from bioetl.application.core.base_transformer.errors import (
    FilteredOutError,
    TransformationError,
)

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer.structural_policy import (
        StructuralPolicyProtocol,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import FilterDecision, SilverFilterConfig
    from bioetl.domain.ports import MetricsPort, TracingPort
    from bioetl.domain.types import BronzeRecord, GoldRecord, SilverRecord

_STRUCTURAL_ACTION_BY_REASON_CODE: dict[str, str] = {
    "required_field_missing": "presence_quarantine",
    "required_field_type_mismatch": "required_type_quarantine",
    "optional_nonnullable_field_type_mismatch": "optional_nonnullable_quarantine",
}
_STRUCTURAL_ACTION_BY_EVENT: dict[str, str] = {
    "silver_structural_type_coerced_to_null": "nullable_type_to_null",
}


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
    semantic_decision: FilterDecision | None,
) -> str | None:
    """Build a bounded comparison label for structural vs semantic filtering."""
    if semantic_decision is None:
        return None
    semantic_state = "reject" if not semantic_decision.include else "pass"
    structural_state = "reject" if structural_rejected else "pass"
    return f"structural_{structural_state}_semantic_{semantic_state}"


def start_transform_span(
    owner: TransformerExecutionOwner,
    context: PipelineContext,
    index: int,
) -> Any:
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


def apply_silver_filter(
    owner: TransformerExecutionOwner,
    context: PipelineContext,
    result: SilverRecord | None,
    index: int,
) -> None:
    """Check silver filter and raise FilteredOutError if excluded."""
    if result is None or owner._silver_filters is None or owner._silver_filters.is_empty():
        return

    decision = owner._silver_filters.evaluate(cast("GoldRecord", result))
    if decision.include:
        return

    context.logger.debug(
        "silver_filter_quarantined",
        provider=owner.provider,
        entity_type=owner.entity_type,
        record_index=index,
        filter_reason_code=decision.reason_code,
        filter_rule_type=decision.rule_type,
        filter_field=decision.field,
    )
    raise FilteredOutError(
        decision.message or "Record excluded by silver filters",
        details={"policy_stage": "semantic", **decision.to_dict()},
    )


def evaluate_semantic_shadow_decision(
    owner: TransformerExecutionOwner,
    result: SilverRecord | None,
) -> FilterDecision | None:
    """Evaluate semantic Silver filters for shadow comparison only."""
    if result is None or owner._silver_filters is None or owner._silver_filters.is_empty():
        return None
    return owner._silver_filters.evaluate(cast("GoldRecord", result))


def record_structural_policy_metrics(
    owner: TransformerExecutionOwner,
    *,
    action: str | None,
    shadow_comparison: str | None,
) -> None:
    """Emit bounded telemetry for structural actions and shadow comparisons."""
    if action is not None:
        owner._metrics.increment_counter(
            "bioetl_structural_policy_events_total",
            1,
            labels={
                "provider": owner.provider,
                "entity_type": owner.entity_type,
                "action": action,
            },
        )
    if shadow_comparison is not None:
        owner._metrics.increment_counter(
            "bioetl_structural_policy_shadow_comparisons_total",
            1,
            labels={
                "provider": owner.provider,
                "entity_type": owner.entity_type,
                "comparison": shadow_comparison,
            },
        )


def apply_structural_policy(
    owner: TransformerExecutionOwner,
    context: PipelineContext,
    result: SilverRecord | None,
    index: int,
) -> SilverRecord | None:
    """Apply schema-aware structural policy before semantic Silver filters."""
    if result is None:
        return None

    outcome = owner._structural_policy.apply(result)
    semantic_shadow_decision = evaluate_semantic_shadow_decision(
        owner,
        outcome.record if not outcome.should_quarantine else result,
    )
    structural_action = classify_structural_action(
        cast("dict[str, object] | None", outcome.details),
        {event.event for event in outcome.events},
    )
    shadow_comparison = classify_structural_shadow_comparison(
        structural_rejected=outcome.should_quarantine,
        semantic_decision=semantic_shadow_decision,
    )
    record_structural_policy_metrics(
        owner,
        action=structural_action,
        shadow_comparison=shadow_comparison,
    )

    for event in outcome.events:
        log_method = getattr(context.logger, event.level)
        log_method(
            event.event,
            provider=owner.provider,
            entity_type=owner.entity_type,
            record_index=index,
            **event.details,
        )

    if not outcome.should_quarantine:
        return outcome.record

    details = outcome.details or {}
    context.logger.debug(
        "silver_structural_quarantined",
        provider=owner.provider,
        entity_type=owner.entity_type,
        record_index=index,
        reason_code=details.get("reason_code"),
        field=details.get("field"),
        action_taken=details.get("action_taken"),
        shadow_comparison=shadow_comparison,
        semantic_shadow_reason_code=(
            semantic_shadow_decision.reason_code
            if semantic_shadow_decision is not None
            else None
        ),
    )
    raise FilteredOutError(
        outcome.quarantine_reason or "Record excluded by structural policy",
        details={
            **details,
            "policy_stage": "structural",
            "shadow_comparison": shadow_comparison,
            "semantic_shadow_reason_code": (
                semantic_shadow_decision.reason_code
                if semantic_shadow_decision is not None
                else None
            ),
        },
    )


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
