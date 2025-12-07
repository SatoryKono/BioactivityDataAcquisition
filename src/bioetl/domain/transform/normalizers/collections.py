"""Normalizers for array and record (dict) types."""

from __future__ import annotations

import json
from typing import Any, Callable, Iterable, Mapping, MutableMapping

from bioetl.domain.transform.normalizers.base import is_missing
from bioetl.domain.transform.normalizers.identifiers import (
    normalize_pcid,
    normalize_uniprot,
)


def normalize_array(
    value: Any, *, item_normalizer: Callable[[Any], Any] | None = None
) -> list[Any]:
    """Normalize array-like value and its elements."""
    if is_missing(value):
        return []

    items = _coerce_to_iterable(value)
    normalized: list[Any] = []
    for idx, item in enumerate(items):
        if is_missing(item):
            continue
        normalized_item = _normalize_array_item(
            item, idx, item_normalizer=item_normalizer
        )
        if not is_missing(normalized_item):
            normalized.append(normalized_item)

    return normalized


def normalize_record(
    value: Any,
    *,
    value_normalizer: Callable[[Any], Any] | None = None,
) -> MutableMapping[str, Any] | None:
    """Normalize mapping/dict values using provided normalizer."""
    if is_missing(value):
        return None

    mapping = _coerce_record_mapping(value)
    normalized: MutableMapping[str, Any] = {}

    for key, item in mapping.items():
        str_key = str(key)
        if is_missing(item):
            continue

        normalized_value = _normalize_record_value(
            str_key,
            item,
            mapping,
            value_normalizer=value_normalizer,
        )
        if not is_missing(normalized_value):
            normalized[str_key] = normalized_value

    return normalized or None


def _coerce_record_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, str):
        value = value.strip()
        if value.startswith("{") and value.endswith("}"):
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Некорректный JSON для записи: {exc}") from exc

            if not isinstance(parsed, Mapping):
                raise ValueError(f"Ожидался словарь, получено {type(parsed).__name__}")
            return dict(parsed)

    if not isinstance(value, Mapping):
        raise ValueError(f"Ожидался словарь, получено {type(value).__name__}")
    # Make a shallow copy to avoid mutating caller-provided mappings and to keep
    # a predictable mapping type downstream.
    return dict(value)


_NO_OVERRIDE = object()


def _normalize_record_value(
    str_key: str,
    item: Any,
    mapping: Mapping[str, Any],
    *,
    value_normalizer: Callable[[Any], Any] | None,
) -> Any:
    try:
        override = _normalize_special_record_value(str_key, item, mapping)
        if override is not _NO_OVERRIDE:
            return override
        return value_normalizer(item) if value_normalizer else item
    except ValueError as exc:
        raise ValueError(f"Некорректное значение в поле '{str_key}': {exc}") from exc


def _coerce_to_iterable(value: Any) -> Iterable[Any]:
    if isinstance(value, str):
        stripped = value.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                return [stripped]

            if isinstance(parsed, (list, tuple)):
                return parsed
            return [parsed]
        if ";" in stripped:
            return [x.strip() for x in stripped.split(";")]
        return [stripped]
    if isinstance(value, (list, tuple)):
        return value
    return [value]


def _normalize_array_item(
    item: Any,
    idx: int,
    *,
    item_normalizer: Callable[[Any], Any] | None = None,
) -> Any:
    try:
        if item_normalizer:
            return item_normalizer(item)
        if isinstance(item, dict):
            return normalize_record(item)
        return str(item)
    except ValueError as exc:
        raise ValueError(
            f"Ошибка нормализации элемента массива на позиции {idx}: {exc}"
        ) from exc


def _normalize_special_record_value(
    str_key: str, item: Any, mapping: Mapping[str, Any]
) -> Any:
    if str_key == "accession":
        return normalize_uniprot(item)
    if str_key == "xref_id":
        source = str(mapping.get("xref_src", "") or "").strip()
        return _normalize_xref_id(source, item)
    if str_key == "target_component_synonyms":
        return _normalize_synonyms(item)
    if str_key == "target_component_xrefs":
        return _normalize_component_xrefs(item)
    return _NO_OVERRIDE


def _normalize_xref_id(source: str, xref_id: Any) -> Any:
    if not source:
        return xref_id
    lowered = source.lower()
    if lowered == "pubchem":
        cid = normalize_pcid(xref_id)
        return cid if cid else xref_id
    if lowered == "uniprot":
        uni_id = normalize_uniprot(xref_id)
        return uni_id if uni_id else xref_id
    return xref_id


def _normalize_synonyms(value: Any) -> Any:
    if is_missing(value):
        return None

    try:
        items = normalize_array(value)
    except ValueError as exc:
        raise ValueError(f"Некорректный список синонимов: {exc}") from exc

    normalized: list[str] = []
    for synonym in items:
        if is_missing(synonym):
            continue
        text = str(synonym).strip()
        if text:
            normalized.append(text)

    if not normalized:
        return None

    return "|".join(sorted(normalized))


def _normalize_component_xrefs(value: Any) -> Any:
    if is_missing(value):
        return None

    try:
        entries = normalize_array(value)
    except ValueError as exc:
        raise ValueError(f"Некорректный список component_xrefs: {exc}") from exc

    normalized_entries: list[str] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            continue

        normalized_entry: dict[str, Any] = {}
        src = str(entry.get("xref_src", "") or "").strip()
        if src:
            normalized_entry["xref_src"] = src
        normalized_entry["xref_id"] = _normalize_xref_id(src, entry.get("xref_id"))

        for key, raw_value in entry.items():
            if key in {"xref_src", "xref_id"}:
                continue
            if is_missing(raw_value) or isinstance(raw_value, (list, dict)):
                continue
            normalized_entry[str(key)] = str(raw_value).strip()

        entry_str = _serialize_mapping(normalized_entry)
        if entry_str:
            normalized_entries.append(entry_str)

    if not normalized_entries:
        return None

    return "|".join(normalized_entries)


def _serialize_mapping(mapping: Mapping[str, Any]) -> str | None:
    if not mapping:
        return None

    parts: list[str] = []
    for key in sorted(mapping.keys()):
        value = mapping[key]
        if value is None or isinstance(value, (list, dict)):
            continue
        parts.append(f"{key}:{value}")

    return "|".join(parts) if parts else None


__all__ = [
    "normalize_array",
    "normalize_record",
]
