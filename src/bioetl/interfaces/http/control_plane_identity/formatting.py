"""Formatting and normalization helpers for identity evidence payloads."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence


def stable_hash(value: object) -> str | None:
    if not is_present(value):
        return None
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def short_value(value: object | None) -> str:
    full = format_full_value(value)
    if not full:
        return ""
    if "," in full:
        return f"{len([item for item in full.split(',') if item.strip()])} items"
    return full if len(full) <= 12 else full[:12]


def format_full_value(value: object | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list | tuple | set):
        return ", ".join(str(item) for item in value if is_present(item))
    if isinstance(value, Mapping):
        return json.dumps(value, sort_keys=True, default=str)
    return str(value).strip()


def is_present(value: object | None) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip()) and value.strip().lower() not in {"none", "null"}
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
