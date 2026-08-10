"""Deterministic integrity helpers for local checkpoint envelopes."""

from __future__ import annotations

import hashlib
import hmac
from collections.abc import Mapping

from bioetl.domain.serialization import serialize_to_canonical_json
from bioetl.domain.types import JsonDict

CHECKPOINT_CHECKSUM_METADATA_KEY = "checkpoint_checksum_valid"
CHECKPOINT_PAYLOAD_SHA256_KEY = "payload_sha256"
_UNSIGNED_ENVELOPE_FIELDS = ("pipeline", "run_id", "metadata", "version")


def strip_reserved_checksum_metadata(metadata: JsonDict | None) -> JsonDict:
    """Copy caller metadata without the adapter-owned checksum verdict."""
    normalized = dict(metadata or {})
    normalized.pop(CHECKPOINT_CHECKSUM_METADATA_KEY, None)
    return normalized


def compute_checkpoint_payload_sha256(envelope: Mapping[str, object]) -> str:
    """Hash the canonical unsigned checkpoint envelope."""
    unsigned: JsonDict = {field: envelope[field] for field in _UNSIGNED_ENVELOPE_FIELDS}
    canonical = serialize_to_canonical_json(unsigned)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def inject_checkpoint_checksum_verdict(
    checkpoint_data: Mapping[str, object],
    metadata: JsonDict,
) -> JsonDict:
    """Inject a recomputed verdict; omit it for digest-less legacy envelopes."""
    normalized = dict(metadata)
    normalized.pop(CHECKPOINT_CHECKSUM_METADATA_KEY, None)
    if CHECKPOINT_PAYLOAD_SHA256_KEY not in checkpoint_data:
        return normalized
    normalized[CHECKPOINT_CHECKSUM_METADATA_KEY] = _checksum_matches(checkpoint_data)
    return normalized


def _checksum_matches(checkpoint_data: Mapping[str, object]) -> bool:
    stored = checkpoint_data.get(CHECKPOINT_PAYLOAD_SHA256_KEY)
    if not isinstance(stored, str) or len(stored) != 64:
        return False
    if any(field not in checkpoint_data for field in _UNSIGNED_ENVELOPE_FIELDS):
        return False
    if not _has_expected_envelope_types(checkpoint_data):
        return False
    try:
        computed = compute_checkpoint_payload_sha256(checkpoint_data)
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(stored, computed)


def _has_expected_envelope_types(checkpoint_data: Mapping[str, object]) -> bool:
    return (
        isinstance(checkpoint_data.get("pipeline"), str)
        and isinstance(checkpoint_data.get("run_id"), str)
        and isinstance(checkpoint_data.get("metadata"), dict)
        and isinstance(checkpoint_data.get("version"), str)
    )


__all__ = [
    "CHECKPOINT_CHECKSUM_METADATA_KEY",
    "CHECKPOINT_PAYLOAD_SHA256_KEY",
    "compute_checkpoint_payload_sha256",
    "inject_checkpoint_checksum_verdict",
    "strip_reserved_checksum_metadata",
]
