"""Canonical replay-taxonomy projection helpers for manifest diagnostics."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy

from bioetl.application.services.control_plane.manifest.replay_taxonomy_fields import (
    LIST_DEFAULTS,
    REPLAY_TAXONOMY_FIELDS,
)


def build_replay_taxonomy_projection(
    **fields: object,
) -> dict[str, object]:
    """Build the canonical replay-taxonomy projection payload.

    Accepts REPLAY_TAXONOMY_FIELDS as kwargs so the public surface stays under
    the Sonar S107 parameter budget. Prefer ``resolve_replay_taxonomy_projection``
    with a mapping for bulk assembly.
    """
    return resolve_replay_taxonomy_projection(fields)



def resolve_replay_taxonomy_projection(
    primary: Mapping[str, object] | None = None,
    *,
    fallback: Mapping[str, object] | None = None,
    defaults: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Resolve replay-taxonomy fields from one canonical projection seam."""
    projection: dict[str, object] = {}
    primary_payload = primary or {}
    fallback_payload = fallback or {}
    defaults_payload = defaults or {}
    for field in REPLAY_TAXONOMY_FIELDS:
        if field in primary_payload:
            value = primary_payload[field]
        elif field in fallback_payload:
            value = fallback_payload[field]
        elif field in defaults_payload:
            value = defaults_payload[field]
        else:
            value = LIST_DEFAULTS.get(field)
        projection[field] = _copy_projection_value(field, value)
    return projection


def resolve_replay_resume_rebuild_verdict(
    *,
    replay_capability: object,
    replay_mode: object,
    continuation_mode: object,
    replay_readiness_verdict: object,
    missing_anchors: object = None,
) -> str:
    """Return the mutually exclusive operator verdict for replay triage."""
    capability = str(replay_capability or "").strip()
    mode = str(replay_mode or "").strip()
    continuation = str(continuation_mode or "").strip()
    readiness = str(replay_readiness_verdict or "").strip()

    if _is_exact_replay_ready(capability, readiness, mode, continuation):
        return "exact_replay_ready"
    if _has_missing_anchors(missing_anchors):
        return "resume_only_degraded"
    if _is_resume_only(capability, mode, continuation):
        return "resume_only"
    if _is_rebuild_only(capability, mode):
        return "rebuild_only"
    return "non_replayable"


def _is_exact_replay_ready(
    capability: str,
    readiness: str,
    mode: str,
    continuation: str,
) -> bool:
    return (
        capability == "exact_replay_supported"
        and readiness == "exact_replay_ready"
        and (mode == "exact_replay" or continuation == "exact_replay")
    )


def _is_resume_only(capability: str, mode: str, continuation: str) -> bool:
    return capability == "resume_only" or mode == "resume" or "resume" in continuation


def _is_rebuild_only(capability: str, mode: str) -> bool:
    return capability == "rebuild_only" or mode in {
        "rebuild",
        "same_data_state_recovery",
        "full_scan_idempotent_rebuild",
    }


def resolve_replay_next_action(verdict: object) -> str:
    """Return compact next-action guidance for a replay triage verdict."""
    value = str(verdict or "").strip()
    if value == "exact_replay_ready":
        return "Use exact replay with manifest, execution fingerprint, and input snapshots."
    if value == "resume_only":
        return "Use checkpoint resume only; do not treat this as exact replay."
    if value == "resume_only_degraded":
        return "Resume is best-effort/degraded; collect missing anchors before replay claims."
    if value == "rebuild_only":
        return "Rebuild from source state; exact replay evidence is unavailable."
    return "Do not replay; required control-plane evidence is missing or inconsistent."


def _has_missing_anchors(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, dict):
        return bool(value)
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list | tuple | set | frozenset):
        return bool(value)
    return bool(value)


def _copy_projection_value(field: str, value: object) -> object:
    """Copy mutable replay-taxonomy values to avoid shared references."""
    if field in LIST_DEFAULTS:
        if isinstance(value, tuple):
            return list(value)
        if isinstance(value, list):
            return list(value)
        return list(LIST_DEFAULTS[field])
    if isinstance(value, dict):
        return dict(value)
    if isinstance(value, list):
        return list(value)
    return deepcopy(value)


__all__ = [
    "REPLAY_TAXONOMY_FIELDS",
    "build_replay_taxonomy_projection",
    "resolve_replay_next_action",
    "resolve_replay_resume_rebuild_verdict",
    "resolve_replay_taxonomy_projection",
]
