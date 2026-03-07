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

if TYPE_CHECKING:
    from bioetl.domain.mapping.classification_data import ClassificationData

__all__ = [
    "PublicationTypeEntry",
    "classify_publication_type",
    "get_classification_table_size",
    "initialize_classification",
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
_PROVIDER_LOOKUPS: dict[str, dict[str, PublicationTypeEntry]] = {}


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
    ``classify_publication_type()``.  Containers are mutated in-place so
    that references obtained via ``from … import _PROVIDER_LOOKUPS`` at
    module collection time see the populated data.

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

    lookup = _get_lookup(provider)
    if lookup is None:
        return None

    if raw_type is not None:
        return lookup.get(raw_type.lower())

    if raw_types_list is not None:
        return _best_match(lookup, raw_types_list)

    return None


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
    return _PROVIDER_LOOKUPS.get(provider.lower())
