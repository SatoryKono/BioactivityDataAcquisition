"""Primitives and constants for the observability contract."""

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

OBSERVABILITY_CORRELATION_FIELDS: Final[tuple[str, ...]] = (
    "manifest_id",
    "entity",
    "run_type",
    "dataset_ref",
    "lineage_fragment_id",
    "effective_config_hash",
    "contract_ref",
    "contract_version",
    "composite_run_id",
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
_DIAGNOSTIC_FAMILY: Final[str] = "diagnostic"
_PIPELINE_LIFECYCLE_FAMILY: Final[str] = "pipeline.lifecycle"
_PIPELINE_PHASE_FAMILY: Final[str] = "pipeline.phase"

_EVENT_FAMILY_EXACT: Final[dict[str, str]] = {
    "pipeline_started": _PIPELINE_LIFECYCLE_FAMILY,
    "pipeline_finished": _PIPELINE_LIFECYCLE_FAMILY,
    "pipeline_failed": _PIPELINE_LIFECYCLE_FAMILY,
    "pipeline_shutdown": _PIPELINE_LIFECYCLE_FAMILY,
    "artifact_published": "artifact",
    "vacuum_completed": "artifact",
}

_EVENT_FAMILY_PREFIXES: Final[tuple[tuple[str, str], ...]] = (
    ("dq_", "dq"),
    ("lineage_", "lineage"),
    ("checkpoint_", "checkpoint"),
    ("composite_", "composite"),
    ("artifact_", "artifact"),
)

_EVENT_FAMILY_SUFFIXES: Final[tuple[tuple[str, str], ...]] = (
    ("_started", _PIPELINE_PHASE_FAMILY),
    ("_completed", _PIPELINE_PHASE_FAMILY),
)


def coerce_non_empty(value: object | None, *, fallback: str) -> str:
    """Coerce arbitrary values to a non-empty string with fallback."""
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def normalize_severity(value: object | None, *, fallback: str) -> str:
    """Normalize severity into the bounded observability vocabulary."""
    normalized = coerce_non_empty(value, fallback=fallback).lower()
    return normalized if normalized in _ALLOWED_SEVERITY_VALUES else "info"


def strip_legacy_keys(normalized: dict[str, object]) -> None:
    """Drop legacy aliases from output context after canonicalization."""
    for legacy_key in OBSERVABILITY_LEGACY_TO_CANONICAL:
        normalized.pop(legacy_key, None)


def has_required_context_value(context: Mapping[str, object], field: str) -> bool:
    """Return True when a required context field is populated."""
    return coerce_non_empty(context.get(field), fallback="") != ""


def _match_event_family_by_suffix(normalized_event_name: str) -> str | None:
    """Match event family by known suffixes."""
    for suffix, family in _EVENT_FAMILY_SUFFIXES:
        if normalized_event_name.endswith(suffix):
            return family
    return None


def _match_event_family_by_prefix(normalized_event_name: str) -> str | None:
    """Match event family by known prefixes."""
    for prefix, family in _EVENT_FAMILY_PREFIXES:
        if normalized_event_name.startswith(prefix):
            return family
    return None


def infer_event_family(event_name: object | None) -> str:
    """Infer coarse event family from canonical event name."""
    normalized_event_name = coerce_non_empty(
        event_name, fallback="unknown_event"
    ).lower()
    exact_match = _EVENT_FAMILY_EXACT.get(normalized_event_name)
    if exact_match is not None:
        return exact_match
    suffix_match = _match_event_family_by_suffix(normalized_event_name)
    if suffix_match is not None:
        return suffix_match
    prefix_match = _match_event_family_by_prefix(normalized_event_name)
    if prefix_match is not None:
        return prefix_match
    return _DIAGNOSTIC_FAMILY


def normalize_optional_correlation_value(value: object | None) -> str | None:
    """Normalize optional correlation values, preserving None for empties."""
    normalized = coerce_non_empty(value, fallback="")
    return normalized if normalized else None


def apply_correlation_defaults(
    *,
    normalized: dict[str, object],
    correlation_defaults: Mapping[str, object] | None,
) -> None:
    """Apply fallback values for optional correlation fields."""
    if correlation_defaults is None:
        return
    for field_name in OBSERVABILITY_CORRELATION_FIELDS:
        if normalized.get(field_name) is not None:
            continue
        fallback_value = normalize_optional_correlation_value(
            correlation_defaults.get(field_name)
        )
        if fallback_value is not None:
            normalized[field_name] = fallback_value
