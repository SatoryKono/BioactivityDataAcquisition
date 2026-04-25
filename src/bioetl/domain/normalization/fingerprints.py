"""Canonical control-plane fingerprint contracts."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

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


def compute_input_snapshot_identity_fingerprint(snapshot_ids: list[str]) -> str | None:
    """Compute a deterministic fingerprint for a canonical snapshot-id set."""
    if not snapshot_ids:
        return None
    return _hash_canonical_payload({"snapshot_ids": snapshot_ids})


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
