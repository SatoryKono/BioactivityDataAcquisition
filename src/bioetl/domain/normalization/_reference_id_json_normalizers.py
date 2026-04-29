"""Pure JSON collection normalizers for provider reference identifiers."""

from __future__ import annotations

from collections.abc import Callable

from bioetl.domain.normalization._reference_id_support import (
    _dedupe_reference_items,
    _json_fallback,
    _normalize_reference_item,
    _parse_json_array,
    _parse_json_object,
    _sort_reference_items,
)
from bioetl.domain.normalization.json import serialize_json_canonical

ReferenceNormalizer = Callable[[object], object]


def normalize_json_array_reference_ids(
    value: object,
    *,
    id_normalizer: ReferenceNormalizer,
    sort_items: bool = True,
) -> object:
    """Canonicalize a JSON array of reference dicts by normalizing each ``id``."""
    parsed = _parse_json_array(value)
    if parsed is None:
        return _json_fallback(value)
    normalized = [_normalize_reference_item(item, id_normalizer) for item in parsed]
    return serialize_json_canonical(
        _sort_reference_items(normalized) if sort_items else normalized
    )


def normalize_json_string_reference_ids(
    value: object,
    *,
    item_normalizer: ReferenceNormalizer,
    sort_items: bool = True,
) -> object:
    """Canonicalize a JSON string-list of provider reference IDs."""
    parsed = _parse_json_array(value)
    if parsed is None:
        return _json_fallback(value)
    normalized = [item_normalizer(item) for item in parsed]
    if sort_items:
        normalized = _dedupe_reference_items(_sort_reference_items(normalized))
    return serialize_json_canonical(normalized)


def normalize_json_object_reference_id(
    value: object,
    *,
    id_normalizer: ReferenceNormalizer,
) -> object:
    """Canonicalize a JSON object by normalizing its ``id`` field."""
    parsed = _parse_json_object(value)
    if parsed is None:
        return _json_fallback(value)
    return serialize_json_canonical(_normalize_reference_item(parsed, id_normalizer))
