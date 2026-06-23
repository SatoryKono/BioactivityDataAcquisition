"""Shared observability contract utilities.

Defines canonical event context fields used across logs and metrics.
Legacy alias keys are no longer migrated after grace-period completion.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from bioetl.domain._observability_contract_primitives import (
    REQUIRED_OBSERVABILITY_FIELDS,
    apply_correlation_defaults,
    coerce_non_empty,
    has_required_context_value,
    infer_event_family,
    normalize_severity,
    strip_legacy_keys,
)

__all__ = [
    "ObservabilityContractPayload",
    "build_observability_contract_payload",
    "enforce_observability_contract_context",
    "is_observability_contract_valid",
    "missing_observability_fields",
    "normalize_observability_context",
    "normalize_observability_metric_labels",
    "normalize_observability_pipeline_label",
]

_VERSIONED_PIPELINE_SUFFIX_RE = re.compile(r"__v\d+_\d+_\d+$")
_UUID_LIKE_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.IGNORECASE,
)
_HASH_LIKE_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{32,}$", re.IGNORECASE)
_WINDOWS_DRIVE_PREFIX_RE = re.compile(r"^[A-Za-z]:[\\/]")


@dataclass(frozen=True)
class ObservabilityContractPayload:
    """Validated event payload with canonical metric labels."""

    context: dict[str, object]
    metric_labels: dict[str, str]


def normalize_observability_context(
    *,
    event_name: str,
    context: Mapping[str, object],
    default_provider: str,
    default_pipeline: str,
    default_run_id: str,
    default_severity: str,
    correlation_defaults: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Normalize event context to canonical keys."""
    normalized: dict[str, object] = {
        key: value for key, value in context.items() if value is not None
    }
    safe_event_name = coerce_non_empty(event_name, fallback="unknown_event")
    safe_provider = coerce_non_empty(default_provider, fallback="unknown")
    safe_pipeline = coerce_non_empty(default_pipeline, fallback="unknown")
    safe_run_id = coerce_non_empty(default_run_id, fallback="unknown")

    strip_legacy_keys(normalized)

    normalized["event"] = coerce_non_empty(
        normalized.get("event"), fallback=safe_event_name
    )
    normalized["provider"] = coerce_non_empty(
        normalized.get("provider"), fallback=safe_provider
    )
    normalized["pipeline"] = coerce_non_empty(
        normalized.get("pipeline"), fallback=safe_pipeline
    )
    normalized["run_id"] = coerce_non_empty(
        normalized.get("run_id"), fallback=safe_run_id
    )

    severity = normalize_severity(
        normalized.get("severity"),
        fallback=normalize_severity(default_severity, fallback="info"),
    )
    normalized["severity"] = severity

    default_error_type = "unknown" if severity == "error" else "none"
    normalized["error_type"] = coerce_non_empty(
        normalized.get("error_type"),
        fallback=default_error_type,
    )
    apply_correlation_defaults(
        normalized=normalized,
        correlation_defaults=correlation_defaults,
    )
    normalized["event_family"] = coerce_non_empty(
        normalized.get("event_family"),
        fallback=infer_event_family(normalized.get("event")),
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
    correlation_defaults: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Normalize and enforce required observability contract fields."""
    safe_event_name = coerce_non_empty(event_name, fallback="unknown_event")
    safe_provider = coerce_non_empty(default_provider, fallback="unknown")
    safe_pipeline = coerce_non_empty(default_pipeline, fallback="unknown")
    safe_run_id = coerce_non_empty(default_run_id, fallback="unknown")
    normalized = normalize_observability_context(
        event_name=safe_event_name,
        context=context,
        default_provider=safe_provider,
        default_pipeline=safe_pipeline,
        default_run_id=safe_run_id,
        default_severity=default_severity,
        correlation_defaults=correlation_defaults,
    )

    missing = missing_observability_fields(normalized)
    if not missing:
        return normalized

    repaired = dict(normalized)
    repaired["event"] = coerce_non_empty(
        repaired.get("event"), fallback=safe_event_name
    )
    repaired["provider"] = coerce_non_empty(
        repaired.get("provider"),
        fallback=safe_provider,
    )
    repaired["pipeline"] = coerce_non_empty(
        repaired.get("pipeline"),
        fallback=safe_pipeline,
    )
    repaired["run_id"] = coerce_non_empty(
        repaired.get("run_id"),
        fallback=safe_run_id,
    )
    repaired["severity"] = normalize_severity(
        repaired.get("severity"),
        fallback=normalize_severity(default_severity, fallback="info"),
    )
    repaired["error_type"] = coerce_non_empty(
        repaired.get("error_type"),
        fallback="unknown" if repaired["severity"] == "error" else "none",
    )
    apply_correlation_defaults(
        normalized=repaired,
        correlation_defaults=correlation_defaults,
    )
    repaired["event_family"] = coerce_non_empty(
        repaired.get("event_family"),
        fallback=infer_event_family(repaired.get("event")),
    )
    return repaired


def is_observability_contract_valid(context: Mapping[str, object]) -> bool:
    """Return ``True`` when all required observability contract fields are present."""
    return len(missing_observability_fields(context)) == 0


def normalize_observability_metric_labels(
    labels: Mapping[str, object],
) -> dict[str, str]:
    """Return canonical labels for ``observability_events_total``."""
    normalized = enforce_observability_contract_context(
        event_name=coerce_non_empty(labels.get("event"), fallback="unknown_event"),
        context=labels,
        default_provider="unknown",
        default_pipeline="unknown",
        default_run_id="unknown",
        default_severity="info",
    )
    event = coerce_non_empty(normalized.get("event"), fallback="unknown_event")
    provider = coerce_non_empty(normalized.get("provider"), fallback="unknown")
    pipeline = normalize_observability_pipeline_label(normalized.get("pipeline"))
    severity = normalize_severity(normalized.get("severity"), fallback="info")
    error_type = coerce_non_empty(normalized.get("error_type"), fallback="none")
    return {
        "event": event,
        "provider": provider,
        "pipeline": pipeline,
        "severity": severity,
        "error_type": error_type,
    }


def normalize_observability_pipeline_label(value: object) -> str:
    """Collapse unbounded runtime values into a canonical low-cardinality label."""
    raw_value = coerce_non_empty(value, fallback="unknown")
    candidate = raw_value.strip()
    if _looks_like_path(candidate):
        candidate = _extract_path_basename(candidate)
    if _looks_like_unbounded_identifier(candidate):
        return "unknown"
    candidate = _sanitize_pipeline_label(candidate)
    if not candidate or _looks_like_unbounded_identifier(candidate):
        return "unknown"
    return candidate


def missing_observability_fields(context: Mapping[str, object]) -> tuple[str, ...]:
    """Return required contract fields missing or empty in *context*."""
    return tuple(
        field
        for field in REQUIRED_OBSERVABILITY_FIELDS
        if not has_required_context_value(context, field)
    )


def build_observability_contract_payload(
    *,
    event_name: str,
    context: Mapping[str, object],
    default_provider: str,
    default_pipeline: str,
    default_run_id: str,
    default_severity: str,
    correlation_defaults: Mapping[str, object] | None = None,
) -> ObservabilityContractPayload:
    """Validate event context once and derive canonical metric labels."""
    normalized = enforce_observability_contract_context(
        event_name=event_name,
        context=context,
        default_provider=default_provider,
        default_pipeline=default_pipeline,
        default_run_id=default_run_id,
        default_severity=default_severity,
        correlation_defaults=correlation_defaults,
    )
    return ObservabilityContractPayload(
        context=normalized,
        metric_labels=normalize_observability_metric_labels(normalized),
    )


def _looks_like_path(value: str) -> bool:
    return "/" in value or "\\" in value or bool(_WINDOWS_DRIVE_PREFIX_RE.match(value))


def _extract_path_basename(value: str) -> str:
    parts = [part for part in re.split(r"[\\/]+", value) if part and part != "."]
    return parts[-1] if parts else ""


def _sanitize_pipeline_label(value: str) -> str:
    normalized = _VERSIONED_PIPELINE_SUFFIX_RE.sub("", value.strip())
    normalized = normalized.replace(".", "_").replace("-", "_").replace(" ", "_")
    normalized = re.sub(r"[\W]+", "_", normalized, flags=re.ASCII)
    normalized = re.sub(r"_+", "_", normalized).strip("_").lower()
    return normalized


def _looks_like_unbounded_identifier(value: str) -> bool:
    return bool(_UUID_LIKE_RE.match(value) or _HASH_LIKE_RE.match(value))
