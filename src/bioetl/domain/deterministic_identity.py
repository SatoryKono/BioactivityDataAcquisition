"""Deterministic identity helpers for pure domain objects."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from enum import Enum
from typing import cast
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


def _canonical_datetime(value: object) -> str:
    return cast(datetime, value).isoformat()


def _canonical_uuid(value: object) -> str:
    return str(cast(UUID, value))


def _canonical_enum(value: object) -> object:
    return cast(Enum, value).value


def _canonical_mapping(value: object) -> dict[str, object]:
    mapping = cast(Mapping[object, object], value)
    canonical: dict[str, object] = {}
    for key, nested in mapping.items():
        if not isinstance(key, str):
            raise TypeError(
                "deterministic identity mappings require string keys; "
                f"got {type(key).__name__}"
            )
        canonical[key] = _canonical_identity_value(nested)
    return {key: canonical[key] for key in sorted(canonical)}


def _is_non_string_sequence(value: object) -> bool:
    return isinstance(value, Sequence) and not isinstance(
        value, (str, bytes, bytearray)
    )


def _canonical_sequence(value: object) -> list[object]:
    return [
        _canonical_identity_value(nested) for nested in cast(Sequence[object], value)
    ]


_CANONICAL_CONVERTERS: tuple[
    tuple[Callable[[object], bool], Callable[[object], object]],
    ...,
] = (
    (lambda value: isinstance(value, datetime), _canonical_datetime),
    (lambda value: isinstance(value, UUID), _canonical_uuid),
    (lambda value: isinstance(value, Enum), _canonical_enum),
    (lambda value: isinstance(value, Mapping), _canonical_mapping),
    (_is_non_string_sequence, _canonical_sequence),
)


def _canonical_identity_value(value: object) -> object:
    """Convert common domain values into canonical JSON-compatible values."""
    for predicate, converter in _CANONICAL_CONVERTERS:
        if predicate(value):
            return converter(value)
    return value


__all__ = ["deterministic_id", "deterministic_uuid"]
