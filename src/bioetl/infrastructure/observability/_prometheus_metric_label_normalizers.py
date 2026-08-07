"""Shared bounded-label normalizers for Prometheus metric policies."""

from __future__ import annotations

from pathlib import PurePath

from bioetl.infrastructure.observability._prometheus_metric_label_vocab import (
    _ALLOWED_ADAPTER_OPERATION_LABELS,
    _ALLOWED_BATCH_LIFECYCLE_EVENT_LABELS,
    _ALLOWED_COMPOSITE_PHASE_ERROR_KIND_LABELS,
    _ALLOWED_COMPOSITE_PHASE_LOSS_KIND_LABELS,
    _ALLOWED_COMPOSITE_PHASE_RECORD_OUTCOME_LABELS,
    _ALLOWED_COMPOSITE_PHASE_RETRY_KIND_LABELS,
    _ALLOWED_DQ_CHECK_TYPE_LABELS,
    _ALLOWED_DQ_DISPOSITION_LABELS,
    _ALLOWED_FILTER_SOURCE_KIND_LABELS,
    _ALLOWED_FLOW_STAGE_LABELS,
    _ALLOWED_OBSERVABILITY_COMPONENT_LABELS,
    _ALLOWED_OBSERVABILITY_MODE_LABELS,
    _ALLOWED_PHASE_LABELS,
    _ALLOWED_POSTRUN_PHASE_LABELS,
    _ALLOWED_PUBLICATION_STATUS_LABELS,
    _ALLOWED_PUBLICATION_TARGET_LABELS,
    _ALLOWED_PUBLICATION_VOCAB_FIELD_LABELS,
    _ALLOWED_PUBLICATION_VOCAB_HANDLING_LABELS,
    _ALLOWED_PUBLICATION_VOCAB_PROVIDER_LABELS,
    _ALLOWED_REASON_LABELS,
    _ALLOWED_RECORD_FLOW_INVARIANT_LABELS,
    _ALLOWED_RECORD_FLOW_INVARIANT_STATUS_LABELS,
    _ALLOWED_RUNTIME_STAGE_LABELS,
    _ALLOWED_SEVERITY_LABELS,
    _ALLOWED_SILVER_FILTER_FIELD_LABELS,
    _ALLOWED_SILVER_FILTER_REASON_CODE_LABELS,
    _ALLOWED_SILVER_FILTER_RULE_TYPE_LABELS,
    _ALLOWED_STAGE_LABELS,
    _ALLOWED_STAGE_MODEL_OUTCOME_LABELS,
    _ALLOWED_STAGE_MODEL_STAGE_LABELS,
    _ALLOWED_STRUCTURAL_ACTION_LABELS,
    _ALLOWED_STRUCTURAL_COMPARISON_LABELS,
    _ALLOWED_TERMINAL_STATUS_LABELS,
    _DYNAMIC_ENDPOINT_SEGMENT_PATTERNS,
    _SOURCE_FILE_CLASS_BY_SUFFIX,
)


def normalize_adapter_endpoint_label(endpoint: str) -> str:
    """Normalize adapter endpoint labels to bounded route-template form.

    Only recognized static segments and braced dynamic templates are preserved.
    Arbitrary free-form segments collapse to ``{param}`` so cardinality stays bounded.
    """
    stripped = endpoint.strip()
    if not stripped:
        return "/unknown"
    path = stripped.split("?", 1)[0]
    normalized_segments: list[str] = []
    for segment in path.split("/"):
        if not segment:
            continue
        normalized_segments.append(_normalize_endpoint_segment(segment))
    if not normalized_segments:
        return "/"
    # Cap path depth to limit combinatorial explosion of route templates.
    if len(normalized_segments) > 8:
        normalized_segments = [*normalized_segments[:7], "{param}"]
    return "/" + "/".join(normalized_segments)


def normalize_source_file_label(source_file: str) -> str:
    """Normalize filter source file labels to bounded source classes."""
    stripped = source_file.strip()
    if not stripped:
        return "unknown"
    path_like = stripped.replace("\\", "/").split("?", 1)[0]
    basename = PurePath(path_like).name
    if not basename:
        return "unknown"
    suffix = PurePath(basename).suffix.lower()
    if suffix in _SOURCE_FILE_CLASS_BY_SUFFIX:
        return _SOURCE_FILE_CLASS_BY_SUFFIX[suffix]
    return "extensionless_file" if "." not in basename else "other_file"


def normalize_filter_source_kind_label(source_kind: str) -> str:
    """Normalize filter source kind labels to a finite source vocabulary."""
    return _normalize_bounded_label(source_kind, _ALLOWED_FILTER_SOURCE_KIND_LABELS)


def normalize_adapter_operation_label(operation: str) -> str:
    """Normalize adapter operation labels to the reviewed bounded vocabulary."""
    return _normalize_bounded_label(operation, _ALLOWED_ADAPTER_OPERATION_LABELS)


def normalize_quarantine_reason(reason: str) -> str:
    """Normalize quarantine reason to a bounded label set."""
    return _normalize_bounded_label(reason, _ALLOWED_REASON_LABELS)


def normalize_silver_filter_reason_code(reason_code: str | None) -> str:
    """Normalize Silver filter reason_code to a bounded label set."""
    return _normalize_bounded_label(
        reason_code or "other", _ALLOWED_SILVER_FILTER_REASON_CODE_LABELS
    )


def normalize_silver_filter_rule_type(rule_type: str | None) -> str:
    """Normalize Silver filter rule_type to a bounded label set."""
    return _normalize_bounded_label(
        rule_type or "other", _ALLOWED_SILVER_FILTER_RULE_TYPE_LABELS
    )


def normalize_silver_filter_field(field: str | None) -> str:
    """Normalize Silver filter field name to a bounded label set."""
    return _normalize_bounded_label(
        field or "other", _ALLOWED_SILVER_FILTER_FIELD_LABELS
    )


def normalize_dq_stage(stage: str) -> str:
    """Normalize DQ stage label to a bounded label set."""
    return _normalize_bounded_label(stage, _ALLOWED_STAGE_LABELS)


def normalize_runtime_stage(stage: str) -> str:
    """Normalize generic runtime stage labels to a bounded label set."""
    return _normalize_bounded_label(stage, _ALLOWED_RUNTIME_STAGE_LABELS)


def normalize_flow_stage(flow_stage: str) -> str:
    """Normalize record-flow stage labels to the canonical bounded set."""
    return _normalize_bounded_label(flow_stage, _ALLOWED_FLOW_STAGE_LABELS)


def normalize_record_flow_invariant(invariant: str) -> str:
    """Normalize record-flow invariant labels to the canonical bounded set."""
    return _normalize_bounded_label(invariant, _ALLOWED_RECORD_FLOW_INVARIANT_LABELS)


def normalize_record_flow_invariant_status(status: str) -> str:
    """Normalize record-flow invariant status labels to the bounded set."""
    return _normalize_bounded_label(
        status, _ALLOWED_RECORD_FLOW_INVARIANT_STATUS_LABELS
    )


def normalize_stage_model_stage(stage: str) -> str:
    """Normalize canonical stage-model stage labels."""
    return _normalize_bounded_label(stage, _ALLOWED_STAGE_MODEL_STAGE_LABELS)


def normalize_stage_model_outcome(outcome: str) -> str:
    """Normalize canonical stage-model outcome labels."""
    return _normalize_bounded_label(outcome, _ALLOWED_STAGE_MODEL_OUTCOME_LABELS)


def normalize_batch_lifecycle_event(event: str) -> str:
    """Normalize bounded batch lifecycle event labels."""
    return _normalize_bounded_label(event, _ALLOWED_BATCH_LIFECYCLE_EVENT_LABELS)


def normalize_runtime_phase(phase: str) -> str:
    """Normalize lifecycle and composite phase labels to a bounded label set."""
    return _normalize_bounded_label(phase, _ALLOWED_PHASE_LABELS)


def normalize_postrun_phase(phase: str) -> str:
    """Normalize postrun subphase labels to the canonical bounded set."""
    return _normalize_bounded_label(phase, _ALLOWED_POSTRUN_PHASE_LABELS)


def normalize_dq_severity(severity: str) -> str:
    """Normalize DQ severity label to a bounded label set."""
    return _normalize_bounded_label(severity, _ALLOWED_SEVERITY_LABELS)


def normalize_dq_disposition(disposition: str) -> str:
    """Normalize DQ disposition labels to the canonical bounded set."""
    return _normalize_bounded_label(disposition, _ALLOWED_DQ_DISPOSITION_LABELS)


def normalize_terminal_status(terminal_status: str) -> str:
    """Normalize terminal run status labels to the bounded set."""
    return _normalize_bounded_label(terminal_status, _ALLOWED_TERMINAL_STATUS_LABELS)


def normalize_publication_target(target: str) -> str:
    """Normalize metrics publication target labels."""
    return _normalize_bounded_label(target, _ALLOWED_PUBLICATION_TARGET_LABELS)


def normalize_publication_status(status: str) -> str:
    """Normalize metrics publication status labels."""
    return _normalize_bounded_label(status, _ALLOWED_PUBLICATION_STATUS_LABELS)


def normalize_publication_vocab_provider(provider: str) -> str:
    """Normalize publication vocabulary provider labels."""
    return _normalize_bounded_label(
        provider,
        _ALLOWED_PUBLICATION_VOCAB_PROVIDER_LABELS,
    )


def normalize_publication_vocab_field(field_name: str) -> str:
    """Normalize publication vocabulary field labels."""
    return _normalize_bounded_label(
        field_name,
        _ALLOWED_PUBLICATION_VOCAB_FIELD_LABELS,
    )


def normalize_publication_vocab_handling(handling: str) -> str:
    """Normalize publication vocabulary handling labels."""
    return _normalize_bounded_label(
        handling,
        _ALLOWED_PUBLICATION_VOCAB_HANDLING_LABELS,
    )


def normalize_composite_phase_record_outcome(outcome: str) -> str:
    """Normalize bounded composite phase record outcomes."""
    return _normalize_bounded_label(
        outcome, _ALLOWED_COMPOSITE_PHASE_RECORD_OUTCOME_LABELS
    )


def normalize_composite_phase_error_kind(error_kind: str) -> str:
    """Normalize bounded composite phase error kinds."""
    return _normalize_bounded_label(
        error_kind, _ALLOWED_COMPOSITE_PHASE_ERROR_KIND_LABELS
    )


def normalize_composite_phase_loss_kind(loss_kind: str) -> str:
    """Normalize bounded composite phase loss kinds."""
    return _normalize_bounded_label(
        loss_kind, _ALLOWED_COMPOSITE_PHASE_LOSS_KIND_LABELS
    )


def normalize_composite_phase_retry_kind(retry_kind: str) -> str:
    """Normalize bounded composite phase retry kinds."""
    return _normalize_bounded_label(
        retry_kind, _ALLOWED_COMPOSITE_PHASE_RETRY_KIND_LABELS
    )


def normalize_observability_component(component: str) -> str:
    """Normalize observability component labels."""
    return _normalize_bounded_label(component, _ALLOWED_OBSERVABILITY_COMPONENT_LABELS)


def normalize_observability_mode(mode: str) -> str:
    """Normalize observability runtime mode labels."""
    return _normalize_bounded_label(mode, _ALLOWED_OBSERVABILITY_MODE_LABELS)


def normalize_dq_check_type(check_type: str) -> str:
    """Normalize DQ check type label to the configured bounded set."""
    return _normalize_bounded_label(check_type, _ALLOWED_DQ_CHECK_TYPE_LABELS)


def normalize_structural_action(action: str) -> str:
    """Normalize structural action label to a bounded label set."""
    return _normalize_bounded_label(action, _ALLOWED_STRUCTURAL_ACTION_LABELS)


def normalize_structural_comparison(comparison: str) -> str:
    """Normalize structural comparison label to a bounded label set."""
    return _normalize_bounded_label(
        comparison,
        _ALLOWED_STRUCTURAL_COMPARISON_LABELS,
    )


def _normalize_endpoint_segment(segment: str) -> str:
    """Collapse likely dynamic path segments into a stable placeholder."""
    if "{" in segment and "}" in segment:
        return segment
    lowered = segment.lower()
    if lowered.startswith("10."):
        return "{id}"
    if any(pattern.match(lowered) for pattern in _DYNAMIC_ENDPOINT_SEGMENT_PATTERNS):
        return "{id}"
    return segment


def _normalize_bounded_label(value: str, allowed_values: frozenset[str]) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return normalized if normalized in allowed_values else "other"
