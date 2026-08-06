"""Formatting and normalization helpers for identity evidence payloads."""

from __future__ import annotations

import hashlib
import json
import re
import uuid
from collections.abc import Iterable, Mapping, Sequence

_PROVIDER_ENTITY_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")


def _json_stable_default(value: object) -> object:
    """Normalize non-JSON-native values for deterministic digests."""
    if isinstance(value, set | frozenset):
        # Sets are unordered; sort stringified members so equal sets hash equal.
        return sorted(value, key=lambda item: json.dumps(item, sort_keys=True, default=str))
    return str(value)


def stable_hash(value: object) -> str | None:
    if not is_present(value):
        return None
    if isinstance(value, set | frozenset):
        value = _json_stable_default(value)
    payload = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        default=_json_stable_default,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _count_csv_items(full: str) -> int:
    return len([item for item in full.split(",") if item.strip()])


def short_value(value: object | None) -> str:
    full = format_full_value(value)
    if not full:
        return ""
    if "," in full:
        return f"{_count_csv_items(full)} items"
    if len(full) <= 12:
        return full
    return full[:12]


def _format_sequence_value(value: Iterable[object]) -> str:
    return ", ".join(str(item) for item in value if is_present(item))


def format_full_value(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list | tuple | set):
        return _format_sequence_value(value)
    if isinstance(value, Mapping):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value).strip()


def _is_present_string(value: str) -> bool:
    text = value.strip()
    if not text:
        return False
    return text.lower() not in {"none", "null"}


def is_present(value: object | None) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return _is_present_string(value)
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return bool(value)
    if isinstance(value, Mapping):
        return bool(value)
    return True


def append_value(values: list[str], raw_value: object) -> None:
    if raw_value is None:
        return
    if isinstance(raw_value, list | tuple | set):
        for item in raw_value:
            append_value(values, item)
        return
    text = str(raw_value).strip()
    if text:
        values.append(text)


def dedupe(values: Iterable[str | None]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def join_non_empty(values: Iterable[object | None], separator: str) -> str | None:
    parts = [str(value).strip() for value in values if str(value or "").strip()]
    return separator.join(parts) if parts else None


def mapping_value(mapping: Mapping[str, object], *keys: str) -> Mapping[str, object]:
    for key in keys:
        value = mapping.get(key)
        if isinstance(value, Mapping):
            return value
    return {}


def validate_run_id_format(value: str) -> bool:
    """Return whether a run id is a UUID version 4."""
    try:
        parsed = uuid.UUID(str(value))
    except ValueError:
        return False
    return parsed.version == 4


def validate_manifest_id_format(value: str) -> bool:
    """Return whether a manifest id follows the HTTP identity contract shape."""
    text = str(value).strip()
    return text.startswith("manifest-") and len(text) > len("manifest-")


def validate_provider_entity_format(value: str) -> bool:
    """Return whether a value follows ``provider.entity`` naming."""
    return bool(_PROVIDER_ENTITY_RE.fullmatch(str(value).strip()))
