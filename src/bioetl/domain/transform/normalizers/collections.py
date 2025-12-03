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
) -> list[Any] | None:
    """Normalize array-like value and its elements."""
    if is_missing(value):
        return None

    if isinstance(value, str):
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        elif ";" in value:
            value = [x.strip() for x in value.split(";")]

    if isinstance(value, (list, tuple)):
        items: Iterable[Any] = value
    else:
        items = [value]

    normalized: list[Any] = []
    for idx, item in enumerate(items):
        if is_missing(item):
            continue

        norm_item: Any = None
        try:
            if item_normalizer:
                norm_item = item_normalizer(item)
            elif isinstance(item, dict):
                norm_item = normalize_record(item)
            else:
                norm_item = str(item)
        except ValueError as exc:
            raise ValueError(
                f"Ошибка нормализации элемента массива на позиции {idx}: {exc}"
            ) from exc

        if not is_missing(norm_item):
            normalized.append(norm_item)

    return normalized if normalized else []


def normalize_record(
    value: Any, *, value_normalizer: Callable[[Any], Any] | None = None
) -> MutableMapping[str, Any] | None:
    """Normalize mapping/dict values using provided normalizer."""
    if is_missing(value):
        return None

    if isinstance(value, str):
        value = value.strip()
        if value.startswith("{") and value.endswith("}"):
            try:
                value = json.loads(value)
            except json.JSONDecodeError as e:
                raise ValueError(f"Некорректный JSON для записи: {e}") from e

    if not isinstance(value, Mapping):
        raise ValueError(
            f"Ожидался словарь, получено {type(value).__name__}"
        )

    normalized: MutableMapping[str, Any] = {}
    for key, item in value.items():
        str_key = str(key)

        if is_missing(item):
            continue

        try:
            if value_normalizer:
                normalized_value = value_normalizer(item)
            else:
                normalized_value = item
        except ValueError as exc:
            raise ValueError(
                f"Некорректное значение в поле '{str_key}': {exc}"
            ) from exc

        if not is_missing(normalized_value):
            normalized[str_key] = normalized_value

    return normalized or None


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
    if is_missing(value):
        return None
    if not isinstance(value, list):
        return None

    normalized: list[dict[str, Any]] = []
    for ref in value:
        if not isinstance(ref, dict):
            continue

        updated = ref.copy()
        src = str(updated.get("xref_src", "")).strip()
        updated["xref_src"] = src if src else None

        xref_id = updated.get("xref_id")

        if src.lower() == "pubchem":
            cid = normalize_pcid(xref_id)
            if cid:
                updated["xref_id"] = cid
        elif src.lower() == "uniprot":
            uni_id = normalize_uniprot(xref_id)
            if uni_id:
                updated["xref_id"] = uni_id

        normalized.append(updated)

    return normalized if normalized else None


__all__ = [
    "normalize_array",
    "normalize_record",
    "normalize_target_components",
    "normalize_cross_references",
]
