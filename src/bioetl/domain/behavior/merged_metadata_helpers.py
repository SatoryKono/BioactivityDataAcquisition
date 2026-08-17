"""Pure selection and identity helpers for merged-metadata explainability."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from bioetl.domain.types import JsonDict

if TYPE_CHECKING:
    from bioetl.domain.models.metadata import CompositeOutputExt


def resolve_priority_order(
    field_name: str,
    field_priorities: dict[str, JsonDict] | None,
) -> tuple[str, ...] | None:
    """Resolve configured provider priority for a merged metadata field."""
    if not field_priorities or field_name not in field_priorities:
        return None
    priority = field_priorities[field_name].get("priority")
    if not isinstance(priority, list):
        return ()
    return tuple(str(item) for item in priority)


def resolve_final_value_source(
    *,
    source_providers: tuple[str, ...],
    priority_order: tuple[str, ...] | None,
) -> str | None:
    """Select the highest-priority available source provider."""
    if not source_providers:
        return None
    if priority_order:
        provider_set = set(source_providers)
        for provider in priority_order:
            if provider in provider_set:
                return provider
    return source_providers[0]


def extract_applied_enrichments(
    composite_metadata: CompositeOutputExt,
) -> tuple[str, ...] | None:
    """Return the enrichers whose composite status is ``applied``."""
    if not composite_metadata.enrichment_status:
        return None
    applied = [
        enricher
        for enricher, status in composite_metadata.enrichment_status.items()
        if status == "applied"
    ]
    return tuple(applied) or None


def public_field_names(record_data: JsonDict) -> list[str]:
    """Return record field names that are not internal metadata keys."""
    return [name for name in record_data if not name.startswith("_")]


def resolve_record_id(record: JsonDict) -> str:
    """Resolve a stable record id, preserving valid falsy identifiers."""
    for key in ("_record_id", "id", "molecule_id"):
        if key in record and record[key] is not None:
            return str(record[key])
    return deterministic_record_id(record)


def deterministic_record_id(record: JsonDict) -> str:
    """Produce a deterministic id for supported non-JSON-native values."""
    payload = json.dumps(
        _normalize_record_id_value(record),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=json_fallback,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalize_record_id_value(value: object) -> object:
    """Normalize nested mappings without order-sensitive mixed-type keys."""
    if isinstance(value, dict):
        return _normalize_record_id_mapping(value)
    if isinstance(value, (list, tuple)):
        return [_normalize_record_id_value(item) for item in value]
    return value


def _normalize_record_id_mapping(value: dict[object, object]) -> dict[str, object]:
    normalized: dict[str, object] = {}
    for key, item in value.items():
        normalized_key = _normalize_record_id_key(key)
        if normalized_key in normalized:
            raise TypeError("Ambiguous mapping keys for deterministic record id")
        normalized[normalized_key] = _normalize_record_id_value(item)
    return normalized


def _normalize_record_id_key(key: object) -> str:
    if isinstance(key, str):
        return key
    if key is None or isinstance(key, (bool, int, float)):
        return json.dumps(key, ensure_ascii=False, allow_nan=False)
    raise TypeError(
        f"Unsupported mapping key for deterministic record id: {type(key).__name__}"
    )


def json_fallback(value: object) -> object:
    """Convert supported non-JSON-native values or reject them explicitly."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (set, frozenset)):
        normalized_items = [_to_json_compatible(item) for item in value]
        return sorted(normalized_items, key=_canonical_json_sort_key)
    return _bytes_or_reject(value)


def _bytes_or_reject(value: object) -> str:
    if isinstance(value, bytes):
        return value.hex()
    raise TypeError(
        f"Unsupported value for deterministic record id: {type(value).__name__}"
    )


def _to_json_compatible(value: object) -> object:
    payload = json.dumps(
        _normalize_record_id_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=json_fallback,
    )
    return json.loads(payload)


def _canonical_json_sort_key(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
