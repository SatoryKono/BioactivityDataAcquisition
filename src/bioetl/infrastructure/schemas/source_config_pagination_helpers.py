"""Legacy pagination promotion helpers for source config schema.

These helpers implement migration-only alias promotion from legacy provider keys
to canonical ``pagination`` fields.
"""

from __future__ import annotations

from bioetl.domain.types import JsonDict

LEGACY_PAGINATION_FIELD_MAP: dict[str, str] = {
    "batch_size": "id_batch_size",
    "page_size": "page_size",
    "max_url_length": "max_url_length",
}


def collect_legacy_pagination_values(
    data: JsonDict,  # Any: YAML config has heterogeneous values
) -> dict[str, object]:
    """Collect legacy pagination-like fields into pagination keys."""
    promoted: dict[str, object] = {}
    for legacy_key, pagination_key in LEGACY_PAGINATION_FIELD_MAP.items():
        value = data.get(legacy_key)
        if value is not None:
            promoted[pagination_key] = value
    return promoted


def merge_legacy_into_pagination(
    pagination: JsonDict,  # Any: YAML config has heterogeneous values
    legacy_values: dict[str, object],
) -> None:
    """Fill missing pagination keys from legacy values."""
    for key, value in legacy_values.items():
        pagination.setdefault(key, value)


def build_pagination_from_legacy(
    data: JsonDict,  # Any: YAML config has heterogeneous values
) -> dict[str, object]:
    """Build pagination dict from legacy fields when section is absent."""
    pagination = collect_legacy_pagination_values(data)
    if data.get("cursor_pagination"):
        pagination["strategy"] = "cursor"
    return pagination
