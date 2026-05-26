"""Deterministic identity helpers for pure domain objects."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from enum import Enum
from uuid import UUID, uuid5

from bioetl.domain.normalization.json import serialize_json_canonical

_DOMAIN_ID_NAMESPACE = UUID("2e4195de-b899-4a13-a6bc-177126826f6d")


def deterministic_uuid(scope: str, payload: Mapping[str, object]) -> UUID:
    """Return a UUIDv5 derived from canonical domain identity inputs."""
    canonical_payload = serialize_json_canonical(
        {
            "payload": _canonical_identity_value(payload),
            "scope": scope,
        }
    )
    return uuid5(_DOMAIN_ID_NAMESPACE, canonical_payload)


def deterministic_id(scope: str, payload: Mapping[str, object]) -> str:
    """Return a stable string identifier for a domain identity payload."""
    return str(deterministic_uuid(scope, payload))


def _canonical_identity_value(value: object) -> object:
    """Convert common domain values into canonical JSON-compatible values."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_identity_value(nested)
            for key, nested in sorted(value.items(), key=lambda item: str(item[0]))
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_canonical_identity_value(nested) for nested in value]
    return value


__all__ = ["deterministic_id", "deterministic_uuid"]
