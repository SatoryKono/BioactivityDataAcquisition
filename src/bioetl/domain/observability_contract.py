"""Shared observability contract utilities.

Defines canonical event context fields used across logs and metrics.
Legacy alias keys are no longer migrated after grace-period completion.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final

__all__ = [
    "ObservabilityContractPayload",
    "build_observability_contract_payload",
    "enforce_observability_contract_context",
    "is_observability_contract_valid",
    "missing_observability_fields",
    "normalize_observability_context",
    "normalize_observability_metric_labels",
]


REQUIRED_OBSERVABILITY_FIELDS: Final[tuple[str, ...]] = (
    "event",
    "provider",
    "pipeline",
    "run_id",
    "error_type",
    "severity",
)

OBSERVABILITY_METRIC_LABEL_FIELDS: Final[tuple[str, ...]] = (
    "event",
    "provider",
    "pipeline",
    "severity",
    "error_type",
)

OBSERVABILITY_LEGACY_TO_CANONICAL: Final[dict[str, str]] = {
    "event_name": "event",
    "provider_name": "provider",
    "pipeline_name": "pipeline",
    "correlation_id": "run_id",
    "log_level": "severity",
}

_ALLOWED_SEVERITY_VALUES: Final[frozenset[str]] = frozenset(
    {"debug", "info", "warning", "error"}
)


@dataclass(frozen=True)
class ObservabilityContractPayload:
    """Validated event payload with canonical metric labels."""

    context: dict[str, object]
    metric_labels: dict[str, str]


def _coerce_non_empty(value: object | None, *, fallback: str) -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _normalize_severity(value: object | None, *, fallback: str) -> str:
    normalized = _coerce_non_empty(value, fallback=fallback).lower()
    return normalized if normalized in _ALLOWED_SEVERITY_VALUES else "info"


def _strip_legacy_keys(normalized: dict[str, object]) -> None:
    """Drop legacy aliases from output context after canonicalization."""
    for legacy_key in OBSERVABILITY_LEGACY_TO_CANONICAL:
        normalized.pop(legacy_key, None)


def _has_required_context_value(context: Mapping[str, object], field: str) -> bool:
    return _coerce_non_empty(context.get(field), fallback="") != ""


def normalize_observability_context(
    *,
    event_name: str,
    context: Mapping[str, object],
    default_provider: str,
    default_pipeline: str,
    default_run_id: str,
    default_severity: str,
) -> dict[str, object]:
    """Normalize event context to canonical keys.

    Args:
        event_name: Canonical event name (e.g., 'pipeline_started').
        context: Raw event context mapping with arbitrary keys.
        default_provider: Fallback provider name if not present in context.
        default_pipeline: Fallback pipeline name if not present in context.
        default_run_id: Fallback run identifier if not present in context.
        default_severity: Fallback severity level if not present in context.

    Returns:
        Dictionary with canonical observability keys and fallback values applied.
    """
    normalized: dict[str, object] = {
        key: value for key, value in context.items() if value is not None
    }
    safe_event_name = _coerce_non_empty(event_name, fallback="unknown_event")
    safe_provider = _coerce_non_empty(default_provider, fallback="unknown")
    safe_pipeline = _coerce_non_empty(default_pipeline, fallback="unknown")
    safe_run_id = _coerce_non_empty(default_run_id, fallback="unknown")

    # Migration grace-period is complete: legacy aliases are ignored.
    _strip_legacy_keys(normalized)

    normalized["event"] = _coerce_non_empty(
        normalized.get("event"), fallback=safe_event_name
    )
    normalized["provider"] = _coerce_non_empty(
        normalized.get("provider"), fallback=safe_provider
    )
    normalized["pipeline"] = _coerce_non_empty(
        normalized.get("pipeline"), fallback=safe_pipeline
    )
    normalized["run_id"] = _coerce_non_empty(
        normalized.get("run_id"), fallback=safe_run_id
    )

    severity = _normalize_severity(
        normalized.get("severity"),
        fallback=_normalize_severity(default_severity, fallback="info"),
    )
    normalized["severity"] = severity

    default_error_type = "unknown" if severity == "error" else "none"
    normalized["error_type"] = _coerce_non_empty(
        normalized.get("error_type"),
        fallback=default_error_type,
    )

    return normalized


def enforce_observability_contract_context(
    *,
    event_name: str,
    context: Mapping[str, object],
    default_provider: str,
    default_pipeline: str,
    default_run_id: str,
    default_severity: str,
) -> dict[str, object]:
    """Normalize and enforce required observability contract fields.

    Args:
        event_name: Canonical event name (e.g., 'pipeline_started').
        context: Raw event context mapping with arbitrary keys.
        default_provider: Fallback provider name if not present in context.
        default_pipeline: Fallback pipeline name if not present in context.
        default_run_id: Fallback run identifier if not present in context.
        default_severity: Fallback severity level if not present in context.

    Returns:
        Dictionary with all required observability contract fields populated.
    """
    safe_event_name = _coerce_non_empty(event_name, fallback="unknown_event")
    safe_provider = _coerce_non_empty(default_provider, fallback="unknown")
    safe_pipeline = _coerce_non_empty(default_pipeline, fallback="unknown")
    safe_run_id = _coerce_non_empty(default_run_id, fallback="unknown")
    normalized = normalize_observability_context(
        event_name=safe_event_name,
        context=context,
        default_provider=safe_provider,
        default_pipeline=safe_pipeline,
        default_run_id=safe_run_id,
        default_severity=default_severity,
    )

    missing = missing_observability_fields(normalized)
    if not missing:
        return normalized

    # Last-resort safety net: never emit incompatible event payloads.
    repaired = dict(normalized)
    repaired["event"] = _coerce_non_empty(
        repaired.get("event"), fallback=safe_event_name
    )
    repaired["provider"] = _coerce_non_empty(
        repaired.get("provider"),
        fallback=safe_provider,
    )
    repaired["pipeline"] = _coerce_non_empty(
        repaired.get("pipeline"),
        fallback=safe_pipeline,
    )
    repaired["run_id"] = _coerce_non_empty(
        repaired.get("run_id"),
        fallback=safe_run_id,
    )
    repaired["severity"] = _normalize_severity(
        repaired.get("severity"),
        fallback=_normalize_severity(default_severity, fallback="info"),
    )
    repaired["error_type"] = _coerce_non_empty(
        repaired.get("error_type"),
        fallback="unknown" if repaired["severity"] == "error" else "none",
    )
    return repaired


def is_observability_contract_valid(context: Mapping[str, object]) -> bool:
    """Return ``True`` when all required observability contract fields are present.

    Args:
        context: Event context mapping to validate against the contract.

    Returns:
        True if all required contract fields are present and non-empty, False otherwise.
    """
    return len(missing_observability_fields(context)) == 0


def normalize_observability_metric_labels(
    labels: Mapping[str, object],
) -> dict[str, str]:
    """Return canonical labels for ``observability_events_total``.

    Uses the same contract-enforcement path as log-event context validation.

    Args:
        labels: Raw metric label mapping with observability fields.

    Returns:
        Dictionary of canonical string metric labels for Prometheus counters.
    """
    normalized = enforce_observability_contract_context(
        event_name=_coerce_non_empty(labels.get("event"), fallback="unknown_event"),
        context=labels,
        default_provider="unknown",
        default_pipeline="unknown",
        default_run_id="unknown",
        default_severity="info",
    )
    event = _coerce_non_empty(normalized.get("event"), fallback="unknown_event")
    provider = _coerce_non_empty(normalized.get("provider"), fallback="unknown")
    pipeline = _coerce_non_empty(normalized.get("pipeline"), fallback="unknown")
    severity = _normalize_severity(normalized.get("severity"), fallback="info")
    error_type = _coerce_non_empty(normalized.get("error_type"), fallback="none")
    return {
        "event": event,
        "provider": provider,
        "pipeline": pipeline,
        "severity": severity,
        "error_type": error_type,
    }


def missing_observability_fields(context: Mapping[str, object]) -> tuple[str, ...]:
    """Return required contract fields missing from context.

    Args:
        context: Event context mapping to check for required observability fields.

    Returns:
        Tuple of field names that are missing or empty in the given context.
    """
    return tuple(
        field
        for field in REQUIRED_OBSERVABILITY_FIELDS
        if not _has_required_context_value(context, field)
    )


def build_observability_contract_payload(
    *,
    event_name: str,
    context: Mapping[str, object],
    default_provider: str,
    default_pipeline: str,
    default_run_id: str,
    default_severity: str,
) -> ObservabilityContractPayload:
    """Validate event context once and derive canonical metric labels.

    Args:
        event_name: Canonical event name (e.g., 'pipeline_started').
        context: Raw event context mapping with arbitrary keys.
        default_provider: Fallback provider name if not present in context.
        default_pipeline: Fallback pipeline name if not present in context.
        default_run_id: Fallback run identifier if not present in context.
        default_severity: Fallback severity level if not present in context.

    Returns:
        ObservabilityContractPayload with normalized context and metric labels.
    """
    normalized = enforce_observability_contract_context(
        event_name=event_name,
        context=context,
        default_provider=default_provider,
        default_pipeline=default_pipeline,
        default_run_id=default_run_id,
        default_severity=default_severity,
    )
    return ObservabilityContractPayload(
        context=normalized,
        metric_labels=normalize_observability_metric_labels(normalized),
    )
