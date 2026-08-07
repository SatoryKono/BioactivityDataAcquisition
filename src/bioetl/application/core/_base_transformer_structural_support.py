# Host/cast bridge residual; prefer Protocol self when rewriting module.
"""Private structural-policy helpers for BaseTransformer execution."""

from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core._base_transformer_execution_support import (
    TransformerExecutionOwner,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import FilterDecision
    from bioetl.domain.types import GoldRecord, SilverRecord

_STRUCTURAL_ACTION_BY_REASON_CODE: dict[str, str] = {
    "required_field_missing": "presence_quarantine",
    "required_field_type_mismatch": "required_type_quarantine",
    "optional_nonnullable_field_type_mismatch": "optional_nonnullable_quarantine",
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


def _raise_if_silver_filtered_out(
    owner: TransformerExecutionOwner,
    context: PipelineContext,
    index: int,
    decision: FilterDecision,
) -> None:
    """Raise FilteredOutError when a Silver filter decision rejects the record."""
    from bioetl.application.core.base_transformer.errors import FilteredOutError

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
        details={"policy_stage": "structural", **decision.to_dict()},
    )


def apply_silver_filter(
    owner: TransformerExecutionOwner,
    context: PipelineContext,
    result: SilverRecord | None,
    index: int,
    *,
    precomputed_decision: FilterDecision | None = None,
) -> None:
    """Check silver filter and raise FilteredOutError if excluded.

    When ``precomputed_decision`` is provided (e.g. from the structural-policy
    shadow evaluation), the filter is not re-evaluated (#7795).
    """
    if (
        result is None
        or owner._silver_filters is None
        or owner._silver_filters.is_empty()
    ):
        return

    decision = (
        precomputed_decision
        if precomputed_decision is not None
        else owner._silver_filters.evaluate(cast("GoldRecord", result))  # pyright: ignore[reportInvalidCast]
    )
    _raise_if_silver_filtered_out(owner, context, index, decision)


def evaluate_semantic_shadow_decision(
    owner: TransformerExecutionOwner,
    result: SilverRecord | None,
) -> FilterDecision | None:
    """Evaluate structural Silver filters for shadow comparison only."""
    if (
        result is None
        or owner._silver_filters is None
        or owner._silver_filters.is_empty()
    ):
        return None
    return owner._silver_filters.evaluate(cast("GoldRecord", result))  # pyright: ignore[reportInvalidCast]


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


def _log_structural_policy_events(
    owner: TransformerExecutionOwner,
    context: PipelineContext,
    index: int,
    events: Iterable[Any],  # Any: structural policy emits provider-defined event objects
) -> None:
    """Emit per-event structural-policy log lines from policy outcome."""
    for event in events:
        log_method = getattr(context.logger, event.level)
        log_method(
            event.event,
            provider=owner.provider,
            entity_type=owner.entity_type,
            record_index=index,
            **event.details,
        )


def apply_structural_policy(
    owner: TransformerExecutionOwner,
    context: PipelineContext,
    result: SilverRecord | None,
    index: int,
) -> SilverRecord | None:
    """Apply schema-aware structural policy before structural Silver filters."""
    from bioetl.application.core.base_transformer.errors import FilteredOutError

    if result is None:
        return None

    outcome = owner._structural_policy.apply(result)
    # Evaluate Silver filters at most once for non-quarantined records (#7795).
    # For quarantine candidates, shadow uses the pre-policy record; for keep
    # path, evaluate on the post-policy record and reuse for enforcement.
    silver_filter_decision = evaluate_semantic_shadow_decision(
        owner,
        outcome.record if not outcome.should_quarantine else result,
    )
    structural_action = classify_structural_action(
        cast("dict[str, object] | None", outcome.details),
        {event.event for event in outcome.events},
    )
    shadow_comparison = classify_structural_shadow_comparison(
        structural_rejected=outcome.should_quarantine,
        silver_filter_decision=silver_filter_decision,
    )
    record_structural_policy_metrics(
        owner,
        action=structural_action,
        shadow_comparison=shadow_comparison,
    )

    _log_structural_policy_events(owner, context, index, outcome.events)

    if not outcome.should_quarantine:
        # Reuse the single evaluation for real enforcement (no second evaluate).
        if silver_filter_decision is not None:
            _raise_if_silver_filtered_out(
                owner,
                context,
                index,
                silver_filter_decision,
            )
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
        silver_filter_shadow_reason_code=(
            silver_filter_decision.reason_code
            if silver_filter_decision is not None
            else None
        ),
    )
    raise FilteredOutError(
        outcome.quarantine_reason or "Record excluded by structural policy",
        details={
            **details,
            "policy_stage": "structural",
            "shadow_comparison": shadow_comparison,
            "silver_filter_shadow_reason_code": (
                silver_filter_decision.reason_code
                if silver_filter_decision is not None
                else None
            ),
        },
    )
