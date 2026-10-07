"""Named canonical byte contracts; provenance is required for historical replay."""

from __future__ import annotations

import math
from collections.abc import Sequence
from enum import StrEnum
from typing import cast

__all__ = ["CanonicalJsonProfile", "validate_canonical_json_value"]


class CanonicalJsonProfile(StrEnum):
    """Existing byte profiles, independent of optional backend availability.

    DOMAIN_V1 preserves domain identities from the locked required-orjson runtime.
    PORT_V1 preserves both canonical port adapters' stdlib re-emission bytes.
    DOMAIN_STDLIB_V1 identifies historical domain fallback when provenance proves it.
    PORT_ORJSON_V1 replays the former port's backend-specific input admission.
    These names are not additional fields in automatically hashed domain events.
    """

    DOMAIN_V1 = "domain-orjson-v1"
    PORT_V1 = "port-stdlib-v1"
    DOMAIN_STDLIB_V1 = "domain-stdlib-v1"
    PORT_ORJSON_V1 = "port-orjson-v1"


def validate_canonical_json_value(value: object) -> None:
    """Reject values whose canonical output would depend on the JSON backend."""
    _reject_numpy_like_array(value)
    if isinstance(value, float):
        _assert_finite_float(value)
        return
    if _is_json_scalar(value):
        return
    _validate_canonical_json_container(value)


def _reject_numpy_like_array(value: object) -> None:
    if not _is_numpy_like_array(value):
        return
    raise TypeError(
        "Canonical JSON serialization requires JSON-compatible values; "
        f"got {type(value).__name__}"
    )


def _validate_canonical_json_container(value: object) -> None:
    if isinstance(value, dict):
        _validate_json_mapping(value)
        return
    if _is_nested_json_sequence(value):
        _validate_json_sequence(cast(Sequence[object], value))
        return
    raise TypeError(
        f"Canonical JSON serialization requires JSON-compatible values; "
        f"got {type(value).__name__}"
    )


def _assert_finite_float(value: float) -> None:
    """Reject one non-finite float value."""
    if math.isfinite(value):
        return
    raise ValueError("Canonical JSON serialization does not allow NaN or Infinity")


def _is_json_scalar(value: object) -> bool:
    """Return whether *value* is a backend-independent JSON scalar."""
    return value is None or isinstance(value, (str, int, bool))


def _validate_json_mapping(value: dict[object, object]) -> None:
    """Validate mapping keys and values for canonical JSON serialization."""
    for key, nested_value in value.items():
        if not isinstance(key, str):
            raise TypeError("Canonical JSON serialization requires string keys")
        validate_canonical_json_value(nested_value)


def _validate_json_sequence(value: Sequence[object]) -> None:
    """Validate every item in a JSON-like sequence."""
    for nested_value in value:
        validate_canonical_json_value(nested_value)


def _is_nested_json_sequence(value: object) -> bool:
    """Return whether the value is a JSON-like sequence."""
    return (
        isinstance(value, Sequence)
        and not isinstance(value, (str, bytes, bytearray))
        and not _is_numpy_like_array(value)
    )


def _is_numpy_like_array(value: object) -> bool:
    """Return whether value looks like a NumPy / pandas array, not JSON."""
    return (
        hasattr(value, "dtype")
        and hasattr(value, "shape")
        and not isinstance(value, (str, bytes, bytearray, memoryview))
    )
