"""Checkpoint freshness payload helpers for health-server HTTP routes."""

from __future__ import annotations

import math


def extract_checkpoint_saved_at_epoch_seconds(
    metadata: dict[str, object],
) -> float | None:
    raw_value = metadata.get("checkpoint_saved_at_epoch_seconds")
    if raw_value is None:
        return None
    try:
        value = float(raw_value)
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def optional_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def build_checkpoint_freshness_unknown_payload(
    *,
    pipeline: str,
    resolved_via: str,
    detail: str,
    evidence_source: str,
    manifest_id: str | None = None,
    checkpoint_run_id: str | None = None,
) -> dict[str, object]:
    return {
        "pipeline": pipeline,
        "resolved_via": resolved_via,
        "manifest_id": manifest_id,
        "checkpoint_run_id": checkpoint_run_id,
        "evidence_source": evidence_source,
        "checkpoint_present": checkpoint_run_id is not None,
        "saved_at_epoch_seconds": None,
        "age_seconds": None,
        "status": "UNKNOWN",
        "detail": detail,
    }


def build_checkpoint_freshness_ok_payload(
    *,
    pipeline: str,
    resolved_via: str,
    manifest_id: str | None,
    checkpoint_run_id: object,
    evidence_source: str,
    saved_at_epoch_seconds: float,
    current_epoch_seconds: float,
    metadata: dict[str, object],
) -> dict[str, object]:
    payload_manifest_id = manifest_id or optional_text(metadata.get("manifest_id"))
    return {
        "pipeline": pipeline,
        "resolved_via": resolved_via,
        "manifest_id": payload_manifest_id,
        "checkpoint_run_id": str(checkpoint_run_id),
        "evidence_source": evidence_source,
        "checkpoint_present": True,
        "saved_at_epoch_seconds": saved_at_epoch_seconds,
        "age_seconds": max(current_epoch_seconds - saved_at_epoch_seconds, 0.0),
        "status": "OK",
        "detail": "Persisted checkpoint freshness derived from checkpoint metadata.",
    }
