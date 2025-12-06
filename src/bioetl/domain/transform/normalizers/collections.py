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
    value: Any, *, value_normalizer: Callable[[Any], Any] | None = None
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
            str_key, item, value_normalizer=value_normalizer
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


def _normalize_record_value(
    str_key: str,
    item: Any,
    *,
    value_normalizer: Callable[[Any], Any] | None,
) -> Any:
    try:
        return value_normalizer(item) if value_normalizer else item
    except ValueError as exc:
        raise ValueError(f"Некорректное значение в поле '{str_key}': {exc}") from exc


def normalize_target_components(value: Any) -> list[dict[str, Any]] | None:
    """Normalize target components list. Standardizes accession codes."""
    if is_missing(value):
        return None
    if not isinstance(value, list):
        return None

    normalized: list[dict[str, Any]] = []
    for component in value:
        if not isinstance(component, dict):
            continue

        updated = component.copy()
        updated_accession = normalize_uniprot(updated.get("accession"))
        if updated_accession:
            updated["accession"] = updated_accession
        normalized.append(updated)

    return normalized if normalized else None


def normalize_cross_references(value: Any) -> list[dict[str, Any]] | None:
    """Normalize cross references list. Standardizes known IDs."""
    if is_missing(value) or not isinstance(value, list):
        return None

    normalized: list[dict[str, Any]] = []
    for ref in value:
        if not isinstance(ref, dict):
            continue

        updated = ref.copy()
        src = str(updated.get("xref_src", "")).strip()
        updated["xref_src"] = src if src else None
        updated["xref_id"] = _normalize_xref_id(src, updated.get("xref_id"))
        normalized.append(updated)

    return normalized if normalized else None


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


__all__ = [
    "normalize_array",
    "normalize_record",
    "normalize_target_components",
    "normalize_cross_references",
]
