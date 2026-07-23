"""Helper functions for normalization profile hashing."""

from __future__ import annotations

import hashlib
import inspect
import json
from collections.abc import Callable, Mapping

FieldNormalizer = Callable[..., object]


def _normalizer_accepts_record_context(normalizer: FieldNormalizer) -> bool:
    """Check if normalizer accepts record context parameter."""
    try:
        parameters = tuple(inspect.signature(normalizer).parameters.values())
    except (TypeError, ValueError):
        return False
    return any(
        parameter.name == "record" or parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in parameters
    )


def _identity(value: object) -> object:
    """Identity function for normalizers."""
    return value


def _normalizer_ref(normalizer: FieldNormalizer) -> str:
    """Return a deterministic reference string for one field normalizer."""
    module_name = getattr(normalizer, "__module__", None)
    qualname = getattr(normalizer, "__qualname__", None)
    if not (isinstance(module_name, str) and isinstance(qualname, str)):
        raise TypeError(
            "normalizer must expose deterministic __module__ and __qualname__; "
            "unstable callables without an identity contract are not supported"
        )
    if qualname == "<lambda>" or qualname.endswith(".<lambda>"):
        raise TypeError(
            "lambda normalizers are not supported; provide a named callable "
            "with stable module/qualname identity"
        )

    semantics = _extract_normalizer_semantics(normalizer)
    if any(semantics.values()):
        return f"{module_name}:{qualname}:{_sha256_hex(semantics)}"
    return f"{module_name}:{qualname}"


def _extract_normalizer_semantics(normalizer: FieldNormalizer) -> dict[str, object]:
    """Extract semantic information from a normalizer for hashing."""
    closure = getattr(normalizer, "__closure__", None) or ()
    return {
        "defaults": _stable_value(getattr(normalizer, "__defaults__", None)),
        "kwdefaults": _stable_value(getattr(normalizer, "__kwdefaults__", None)),
        "closure": [_stable_value(cell.cell_contents) for cell in closure],
    }


def _sha256_hex(payload: object) -> str:
    """Return canonical SHA256 hex digest for one JSON-serializable payload."""
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _stable_value(value: object) -> object:
    """Convert value to a JSON-serializable, hash-stable representation."""
    if isinstance(value, Mapping):
        return _stable_mapping(value)
    if isinstance(value, (list, tuple)):
        return _stable_sequence(value)
    if isinstance(value, (set, frozenset)):
        return _stable_set(value)
    return _stable_primitive(value)


def _stable_primitive(value: object) -> object:
    """Convert primitive or special types to stable representation."""
    if isinstance(value, bytes):
        return value.hex()
    if callable(value):
        return _stable_callable(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return repr(value)


def _stable_mapping(value: Mapping[object, object]) -> dict[str, object]:
    """Convert mapping to sorted dict with stable values."""
    return {
        str(k): _stable_value(v)
        for k, v in sorted(value.items(), key=lambda i: str(i[0]))
    }


def _stable_sequence(value: list[object] | tuple[object, ...]) -> list[object]:
    """Convert sequence to list with stable values."""
    return [_stable_value(v) for v in value]


def _stable_set(value: set[object] | frozenset[object]) -> list[object]:
    """Convert set to sorted list with stable values."""
    normalized = [_stable_value(item) for item in value]
    return sorted(
        normalized,
        key=lambda item: json.dumps(item, sort_keys=True, default=str),
    )


def _stable_callable(value: object) -> dict[str, str]:
    """Extract stable metadata from callable."""
    return {
        "module": getattr(value, "__module__", type(value).__module__),
        "qualname": getattr(value, "__qualname__", type(value).__qualname__),
    }
