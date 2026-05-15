"""Canonical control-plane fingerprint contracts."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping
from datetime import datetime

from bioetl.domain.normalization.json import serialize_json_canonical

__all__ = [
    "compute_degraded_runtime_anchor_fingerprint",
    "compute_execution_identity_fingerprint",
    "compute_input_snapshot_identity_fingerprint",
    "compute_manifest_execution_fingerprint",
]


def _hash_canonical_payload(payload: Mapping[str, object]) -> str:
    """Return lowercase SHA256 over canonical JSON bytes.

    Optional control-plane fields are hashed only when populated so nullable
    contract expansions do not retroactively perturb existing fingerprints.
    """
    canonical_payload = {
        key: value for key, value in payload.items() if value is not None
    }
    canonical = serialize_json_canonical(canonical_payload)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_execution_identity_fingerprint(payload: Mapping[str, object]) -> str:
    """Compute the canonical execution-identity fingerprint contract."""
    return _hash_canonical_payload(payload)


_SNAPSHOT_IDENTITY_FIELDS: tuple[str, ...] = (
    "snapshot_id",
    "content_hash",
    "immutable_uri",
    "query_fingerprint",
    "storage_provider",
    "object_bucket",
    "object_key",
    "object_version_id",
    "etag",
    "last_modified",
    "captured_at",
)


def _snapshot_field_value(snapshot: object, field_name: str) -> object | None:
    if isinstance(snapshot, Mapping):
        return snapshot.get(field_name)
    return getattr(snapshot, field_name, None)


def _normalize_snapshot_field_value(value: object | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    text = str(value).strip()
    return text or None


def _normalize_input_snapshot_identity_record(
    snapshot: object,
) -> dict[str, str] | None:
    record = {
        field_name: normalized
        for field_name in _SNAPSHOT_IDENTITY_FIELDS
        for normalized in [
            _normalize_snapshot_field_value(_snapshot_field_value(snapshot, field_name))
        ]
        if normalized is not None
    }
    if "snapshot_id" not in record:
        return None
    return record


def _input_snapshot_identity_sort_key(snapshot: Mapping[str, str]) -> tuple[str, ...]:
    return tuple(
        snapshot.get(field_name, "") for field_name in _SNAPSHOT_IDENTITY_FIELDS
    )


def compute_input_snapshot_identity_fingerprint(
    snapshots: list[object],
) -> str | None:
    """Compute a deterministic fingerprint for canonical immutable snapshot refs."""
    normalized_snapshots = sorted(
        (
            record
            for snapshot in snapshots
            for record in [_normalize_input_snapshot_identity_record(snapshot)]
            if record is not None
        ),
        key=_input_snapshot_identity_sort_key,
    )
    if not normalized_snapshots:
        return None
    return _hash_canonical_payload({"input_snapshots": normalized_snapshots})


def compute_manifest_execution_fingerprint(payload: Mapping[str, object]) -> str:
    """Backward-compatible alias for the canonical execution-identity helper.

    Historically this helper was described as a full RunManifest fingerprint.
    The canonical contract is now the execution-identity payload shared across
    manifest, checkpoint, and runtime compatibility surfaces. Callers are still
    expected to pass an already-normalized payload.
    """

    return compute_execution_identity_fingerprint(payload)


def compute_degraded_runtime_anchor_fingerprint(
    payload: Mapping[str, object | None],
) -> str:
    """Compute the explicitly degraded runtime-anchor compatibility fingerprint.

    This helper is intentionally narrower than the canonical execution identity.
    It exists only for legacy compatibility paths when a full execution
    fingerprint or canonical checkpoint-execution payload is unavailable.
    Callers are expected to pass the already-normalized payload produced by
    `normalize_runtime_anchor_payload()`.
    """

    return compute_execution_identity_fingerprint(payload)
