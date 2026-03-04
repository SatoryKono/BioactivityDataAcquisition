"""Shared observability contract utilities.

Defines canonical event context fields used across logs and metrics, plus
compatibility mapping for legacy field names during migration.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

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

OBSERVABILITY_CANONICAL_TO_LEGACY: Final[dict[str, str]] = {
    canonical: legacy for legacy, canonical in OBSERVABILITY_LEGACY_TO_CANONICAL.items()
}

_ALLOWED_SEVERITY_VALUES: Final[frozenset[str]] = frozenset(
    {"debug", "info", "warning", "error"}
)


def _coerce_non_empty(value: object | None, *, fallback: str) -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _normalize_severity(value: object | None, *, fallback: str) -> str:
    normalized = _coerce_non_empty(value, fallback=fallback).lower()
    return normalized if normalized in _ALLOWED_SEVERITY_VALUES else "info"


def _migrate_legacy_keys(normalized: dict[str, object]) -> None:
    """Promote legacy context keys to their canonical equivalents in-place."""
    for legacy_key, canonical_key in OBSERVABILITY_LEGACY_TO_CANONICAL.items():
        if canonical_key not in normalized and legacy_key in normalized:
            normalized[canonical_key] = normalized[legacy_key]


def _write_dual_aliases(normalized: dict[str, object]) -> None:
    """Write legacy aliases for canonical keys (dashboard migration period)."""
    for canonical_key, legacy_key in OBSERVABILITY_CANONICAL_TO_LEGACY.items():
        normalized.setdefault(legacy_key, normalized[canonical_key])


def _has_required_context_value(context: Mapping[str, object], field: str) -> bool:
    return _coerce_non_empty(context.get(field), fallback="") != ""


def _has_event_value(context: Mapping[str, object]) -> bool:
    return _has_required_context_value(context, "event") or _has_required_context_value(
        context, "event_name"
    )


def normalize_observability_context(
    *,
    event_name: str,
    context: Mapping[str, object],
    default_provider: str,
    default_pipeline: str,
    default_run_id: str,
    default_severity: str,
) -> dict[str, object]:
    """Normalize event context to canonical keys and keep dual-write aliases."""
    normalized: dict[str, object] = {
        key: value for key, value in context.items() if value is not None
    }

    _migrate_legacy_keys(normalized)

    normalized["event"] = _coerce_non_empty(
        normalized.get("event"), fallback=event_name
    )
    normalized["provider"] = _coerce_non_empty(
        normalized.get("provider"), fallback=default_provider
    )
    normalized["pipeline"] = _coerce_non_empty(
        normalized.get("pipeline"), fallback=default_pipeline
    )
    normalized["run_id"] = _coerce_non_empty(
        normalized.get("run_id"), fallback=default_run_id
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

    _write_dual_aliases(normalized)

    return normalized


def normalize_observability_metric_labels(
    labels: Mapping[str, object],
) -> dict[str, str]:
    """Return canonical labels for ``observability_events_total``."""
    normalized = normalize_observability_context(
        event_name=_coerce_non_empty(labels.get("event"), fallback="unknown_event"),
        context=labels,
        default_provider="unknown",
        default_pipeline="unknown",
        default_run_id="unknown",
        default_severity=_coerce_non_empty(labels.get("severity"), fallback="info"),
    )
    return {
        key: _coerce_non_empty(normalized.get(key), fallback="unknown")
        for key in OBSERVABILITY_METRIC_LABEL_FIELDS
    }


def missing_observability_fields(context: Mapping[str, object]) -> tuple[str, ...]:
    """Return required contract fields missing from context."""
    return tuple(
        field
        for field in REQUIRED_OBSERVABILITY_FIELDS
        if not (
            _has_event_value(context)
            if field == "event"
            else _has_required_context_value(context, field)
        )
    )
