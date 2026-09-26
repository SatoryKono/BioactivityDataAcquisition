"""Support helpers for immutable workflow run options."""

from __future__ import annotations

_RUN_OPTIONS_MULTI_FILTER_IDS = "multi_filter_ids"
_RUN_OPTIONS_FILTER_IDS = "filter_ids"
_PERSISTENCE_PROFILE_RANK = {
    "degraded_observable": 0,
    "replay_ready": 1,
    "forensic_grade": 2,
}

__all__ = [
    "prefer_override",
    "prefer_stricter_persistence_profile",
    "serialize_workflow_run_option_value",
]


def prefer_override[RunOptionValue](
    current: RunOptionValue | None,
    override: RunOptionValue | None,
) -> RunOptionValue | None:
    """Return the override when it is set, otherwise keep the current value."""
    return override if override is not None else current


def prefer_stricter_persistence_profile(
    current: str | None,
    override: str | None,
) -> str | None:
    """Preserve the strongest reproducibility floor across workflow overrides."""
    if current is None:
        return override
    if override is None:
        return current
    current_rank = _PERSISTENCE_PROFILE_RANK.get(current, -1)
    override_rank = _PERSISTENCE_PROFILE_RANK.get(override, -1)
    if current_rank >= override_rank:
        return current
    return override


def serialize_workflow_run_option_value(field_name: str, value: object) -> object:
    """Serialize one workflow run-option value for JSON-compatible mappings."""
    if field_name == _RUN_OPTIONS_MULTI_FILTER_IDS:
        return _serialize_multi_filter_ids(value)
    if field_name == _RUN_OPTIONS_FILTER_IDS:
        return _serialize_filter_ids(value)
    return value


def _serialize_multi_filter_ids(value: object) -> object:
    """Serialize ``multi_filter_ids`` into a JSON-compatible mapping."""
    if not isinstance(value, dict):
        return value
    return {key: list(items) for key, items in value.items()}


def _serialize_filter_ids(value: object) -> object:
    """Serialize ``filter_ids`` into a JSON-compatible list."""
    if not isinstance(value, tuple):
        return value
    return list(value)
