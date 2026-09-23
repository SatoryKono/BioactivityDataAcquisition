"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from typing import cast

from memory.graph.sync_pkg.workflow_environment_mapping_name import (
    _sorted_string_items,
    _workflow_environment_mapping_name,
)

__all__ = [
    "_WORKFLOW_FAMILY_RULES",
    "_workflow_environment_name",
    "_workflow_on_payload",
    "_workflow_trigger_names",
]

_WORKFLOW_FAMILY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("release", ("release", "publish")),
    ("docs", ("docs", "doc")),
    ("governance", ("governance", "schema", "quality")),
    ("docker", ("docker",)),
)


def _workflow_on_payload(payload: dict[str, object]) -> object:
    if "on" in payload:
        return payload.get("on")
    return cast(dict[object, object], payload).get(True)


def _workflow_trigger_names(payload: dict[str, object]) -> tuple[str, ...]:
    trigger_payload = _workflow_on_payload(payload)
    if isinstance(trigger_payload, str):
        return (trigger_payload,)
    if isinstance(trigger_payload, list):
        return _sorted_string_items(trigger_payload)
    if isinstance(trigger_payload, dict):
        return _sorted_string_items(trigger_payload.keys())
    return ()


def _workflow_environment_name(job_payload: dict[str, object]) -> str | None:
    environment_payload = job_payload.get("environment")
    if isinstance(environment_payload, str):
        return environment_payload
    return _workflow_environment_mapping_name(environment_payload)
