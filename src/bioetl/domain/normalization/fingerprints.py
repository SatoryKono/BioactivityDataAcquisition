"""Canonical control-plane fingerprint contracts."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping

from bioetl.domain.normalization.json import serialize_json_canonical

__all__ = [
    "compute_manifest_execution_fingerprint",
    "compute_runtime_anchor_fingerprint",
]


def _hash_canonical_payload(payload: Mapping[str, object]) -> str:
    """Return lowercase SHA256 over canonical JSON bytes."""
    canonical = serialize_json_canonical(dict(payload))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def compute_manifest_execution_fingerprint(payload: Mapping[str, object]) -> str:
    """Compute the canonical RunManifest execution fingerprint.

    This is the full manifest-identity contract used for replay/equivalence
    checks. Callers are expected to pass the already-normalized manifest
    payload produced by `normalize_run_manifest_spec()`.
    """

    return _hash_canonical_payload(payload)


def compute_runtime_anchor_fingerprint(
    payload: Mapping[str, object | None],
) -> str:
    """Compute the canonical runtime-anchor compatibility fingerprint.

    This is intentionally narrower than the full manifest execution
    fingerprint. It covers the normalized control-plane anchor payload used
    for checkpoint/resume compatibility when a full manifest fingerprint is
    unavailable. Callers are expected to pass the already-normalized payload
    produced by `normalize_runtime_anchor_payload()`.
    """

    return _hash_canonical_payload(payload)
