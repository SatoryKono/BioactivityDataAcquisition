"""Unified publication type classification for cross-provider harmonization.

This module provides runtime lookup/classification logic for publication types.
Classification data is loaded from a JSON asset at startup via
``initialize_classification()``.

Source of truth:
- configs/enums/publication_type_classification.csv
- Generated JSON: configs/enums/publication_type_classification.asset.v1.json
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.normalization.text import normalize_string

if TYPE_CHECKING:
    from bioetl.domain.mapping.classification_data import ClassificationData

__all__ = [
    "PublicationTypeEntry",
    "build_publication_type_classification_payload",
    "classify_publication_type",
    "get_classification_table_size",
    "initialize_classification",
    "is_initialized",
    "normalize_publication_classification_field",
]


@dataclass(frozen=True, slots=True)
class PublicationTypeEntry:
    """Single entry in the unified publication type classification.

    Attributes:
        unified_type: Level 3 type name (e.g. ``Journal Article``).
        subclass: Level 2 grouping (e.g. ``Original Experimental Data``).
        class_code: Level 1 code: ``EXP``, ``REV``, or ``PEER``.
        specificity: Row number from CSV (higher means more specific).
    """

    unified_type: str
    subclass: str
    class_code: str
    specificity: int


# Module-level state, populated by initialize_classification().
# These containers are mutated in-place so that imports at collection time
# see the updated data after initialization.
_data: ClassificationData | None = None
_ENTRY_BY_SPECIFICITY: list[PublicationTypeEntry] = []
_ENTRY_BY_UNIFIED_TYPE: dict[str, PublicationTypeEntry] = {}
_PROVIDER_LOOKUPS: dict[str, dict[str, PublicationTypeEntry]] = {}


def is_initialized() -> bool:
    """Return whether classification data has been loaded.

    Returns:
        True if ``initialize_classification()`` has been called successfully.
    """
    return bool(_PROVIDER_LOOKUPS)


def get_classification_table_size() -> int:
    """Return the number of entries in the classification table.

    Returns:
        Number of entries currently loaded in the classification table.
    """
    return len(_ENTRY_BY_SPECIFICITY)


def _build_lookup(
    entries: tuple[PublicationTypeEntry, ...],
    row_index: dict[str, int],
) -> dict[str, PublicationTypeEntry]:
    """Build provider lookup using precomputed row-index mapping."""
    max_idx = len(entries)
    return {
        raw_key: entries[idx - 1]
        for raw_key, idx in row_index.items()
        if 0 < idx <= max_idx
    }


def initialize_classification(data: ClassificationData) -> None:
    """Initialize classification lookups from loaded data.

    Must be called once at application startup before any calls to
    ``classify_publication_type()``.  Safe to call multiple times
    (idempotent).  Containers are mutated in-place so that references
    obtained via ``from … import _PROVIDER_LOOKUPS`` at module collection
    time see the populated data.

    Args:
        data: ClassificationData loaded from the JSON asset file.
    """
    global _data

    _data = data

    entries = [
        PublicationTypeEntry(
            unified_type=ut,
            subclass=sc,
            class_code=cc,
            specificity=idx,
        )
        for idx, (ut, sc, cc) in enumerate(data.entry_cores, start=1)
    ]
    _ENTRY_BY_SPECIFICITY.clear()
    _ENTRY_BY_SPECIFICITY.extend(entries)

    entries_tuple = tuple(entries)
    _ENTRY_BY_UNIFIED_TYPE.clear()
    _ENTRY_BY_UNIFIED_TYPE.update(
        {
            _canonical_publication_type_key(entry.unified_type): entry
            for entry in entries_tuple
        }
    )
    _PROVIDER_LOOKUPS.clear()
    _PROVIDER_LOOKUPS.update(
        {
            "openalex": _build_lookup(entries_tuple, data.openalex_row_index),
            "crossref": _build_lookup(entries_tuple, data.crossref_row_index),
            "pubmed": _build_lookup(entries_tuple, data.pubmed_row_index),
            "semanticscholar": _build_lookup(entries_tuple, data.s2_row_index),
            "semantic_scholar": _build_lookup(entries_tuple, data.s2_row_index),
            "s2": _build_lookup(entries_tuple, data.s2_row_index),
        }
    )


def _classify_chembl_type(
    raw_type: str | None,
    raw_types_list: list[str] | None,
) -> PublicationTypeEntry | None:
    if raw_type is not None:
        return _classify_chembl_publication_type(raw_type)
    if raw_types_list is not None:
        return _best_chembl_match(raw_types_list)
    return None


def _classify_non_chembl_type(
    lookup: dict[str, PublicationTypeEntry],
    raw_type: str | None,
    raw_types_list: list[str] | None,
) -> PublicationTypeEntry | None:
    if raw_type is not None:
        return lookup.get(raw_type.strip().lower())
    if raw_types_list is not None:
        return _best_match(lookup, raw_types_list)
    return None


def classify_publication_type(
    provider: str,
    raw_type: str | None = None,
    raw_types_list: list[str] | None = None,
) -> PublicationTypeEntry | None:
    """Classify publication type using unified 3-level hierarchy.

    For single-value providers (OpenAlex, CrossRef), ``raw_type`` is used.
    For multi-value providers (PubMed, Semantic Scholar), the most specific
    match from ``raw_types_list`` is returned.

    Args:
        provider: Provider name (e.g., 'openalex', 'pubmed', 'crossref', 'semanticscholar').
        raw_type: Single raw type string for single-value providers. Defaults to None.
        raw_types_list: List of raw type strings for multi-value providers. Defaults to None.

    Returns:
        PublicationTypeEntry if a match is found, None if provider is unknown
        or no match is found.

    Raises:
        RuntimeError: If ``initialize_classification()`` has not been called.
    """
    if not _PROVIDER_LOOKUPS:
        msg = (
            "Classification data not initialized. "
            "Call initialize_classification() at startup."
        )
        raise RuntimeError(msg)

    provider_lower = provider.lower()
    if provider_lower == "chembl":
        return _classify_chembl_type(raw_type, raw_types_list)

    lookup = _get_lookup(provider)
    if lookup is None:
        return None

    return _classify_non_chembl_type(lookup, raw_type, raw_types_list)


def build_publication_type_classification_payload(
    provider: str,
    raw_type: str | None = None,
    raw_types_list: list[str] | None = None,
    *,
    raw_field_name: str = "publication_type_raw",
) -> dict[str, str | None]:
    """Build the raw-provider and unified classification payload.

    The default raw field is intentionally named ``publication_type_raw`` for
    callers that need an explicit sidecar field. Existing Silver schemas use
    ``publication_type`` for the same raw value and pass that name explicitly.
    """
    raw_value = _raw_publication_type(raw_type=raw_type, raw_types_list=raw_types_list)
    entry = classify_publication_type(
        provider,
        raw_type=raw_type,
        raw_types_list=raw_types_list,
    )
    payload: dict[str, str | None] = {
        raw_field_name: raw_value,
        "publication_type_unified": None,
        "publication_subclass": None,
        "publication_class": None,
    }
    if entry is not None:
        payload.update(
            {
                "publication_type_unified": entry.unified_type,
                "publication_subclass": entry.subclass,
                "publication_class": entry.class_code,
            }
        )
    return payload


def _find_matching_classification_value(
    normalized: str,
    allowed: frozenset[str],
) -> str | None:
    for allowed_value in allowed:
        if normalized.lower() == allowed_value.lower():
            return allowed_value
    return None


def normalize_publication_classification_field(
    field_name: str,
    value: object,
) -> object:
    """Normalize derived publication classification fields against loaded taxonomy."""
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    normalized = normalize_string(value)
    if normalized is None:
        return None
    allowed = _classification_values(field_name)
    if not allowed:
        return normalized
    return _find_matching_classification_value(normalized, allowed)


def _best_match(
    lookup: dict[str, PublicationTypeEntry],
    raw_types: list[str],
) -> PublicationTypeEntry | None:
    """Return the most specific entry among matching raw types."""
    matches = [
        entry
        for raw in raw_types
        if raw and (entry := lookup.get(raw.strip().lower())) is not None
    ]
    return max(matches, key=lambda entry: entry.specificity, default=None)


def _get_lookup(provider: str) -> dict[str, PublicationTypeEntry] | None:
    """Return provider lookup dict, if provider is supported."""
    provider_key = provider.lower()
    if provider_key == "chembl":
        return {}
    return _PROVIDER_LOOKUPS.get(provider_key)


_CLASSIFICATION_FIELD_DISPATCH = {
    "publication_type_unified": lambda: frozenset(
        entry.unified_type for entry in _ENTRY_BY_SPECIFICITY
    ),
    "publication_subclass": lambda: frozenset(
        entry.subclass for entry in _ENTRY_BY_SPECIFICITY
    ),
    "publication_class": lambda: frozenset(
        entry.class_code for entry in _ENTRY_BY_SPECIFICITY
    ),
}


def _classification_values(field_name: str) -> frozenset[str]:
    getter = _CLASSIFICATION_FIELD_DISPATCH.get(field_name)
    if getter:
        return getter()
    raise ValueError(f"Unknown publication classification field: {field_name}")


def _filter_and_strip_types(raw_types_list: list[str]) -> list[str]:
    return [
        str(item).strip()
        for item in raw_types_list
        if item is not None and str(item).strip()
    ]


def _process_raw_types_list(raw_types_list: list[str] | None) -> str | None:
    if not raw_types_list:
        return None

    processed_parts = _filter_and_strip_types(raw_types_list)
    return "|".join(processed_parts) if processed_parts else None


def _raw_publication_type(
    *,
    raw_type: str | None,
    raw_types_list: list[str] | None,
) -> str | None:
    if raw_type is not None:
        raw = raw_type.strip()
        return raw or None
    return _process_raw_types_list(raw_types_list)


def _canonical_publication_type_key(value: str) -> str:
    from bioetl.domain.mapping.publication_type_mapping import (
        normalize_publication_type,
    )

    return normalize_publication_type(value) or value.strip().lower()


def _classify_chembl_publication_type(raw_type: str) -> PublicationTypeEntry | None:
    return _ENTRY_BY_UNIFIED_TYPE.get(_canonical_publication_type_key(raw_type))


def _best_chembl_match(raw_types: list[str]) -> PublicationTypeEntry | None:
    matches = [
        entry
        for raw in raw_types
        if raw and (entry := _classify_chembl_publication_type(raw.strip())) is not None
    ]
    return max(matches, key=lambda entry: entry.specificity, default=None)
