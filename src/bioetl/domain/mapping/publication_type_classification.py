"""Unified publication type classification for cross-provider harmonization.

This module provides runtime lookup/classification logic for publication types.
The giant static table is stored in a generated domain data-asset module:
`bioetl.domain.mapping.generated.publication_type_classification_data`.

Source of truth:
- configs/enums/publication_type_classification.csv
- Generated via: scripts/generate_publication_type_classification_artifacts.py
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from bioetl.domain.mapping.generated.publication_type_classification_data import (
    _CLASSIFICATION_TABLE,
    _CROSSREF_ROW_INDEX,
    _ENTRY_CORE,
    _OPENALEX_ROW_INDEX,
    _PUBMED_ROW_INDEX,
    _S2_ROW_INDEX,
    CLASSIFICATION_TABLE_SIZE,
)

__all__ = [
    "CLASSIFICATION_TABLE_SIZE",
    "_CLASSIFICATION_TABLE",
    "PublicationTypeEntry",
    "classify_publication_type",
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


_ENTRY_BY_SPECIFICITY: Final[tuple[PublicationTypeEntry, ...]] = tuple(
    PublicationTypeEntry(
        unified_type=unified_type,
        subclass=subclass,
        class_code=class_code,
        specificity=row_idx,
    )
    for row_idx, (unified_type, subclass, class_code) in enumerate(_ENTRY_CORE, start=1)
)


def _build_lookup_from_row_index(
    row_index: dict[str, int],
) -> dict[str, PublicationTypeEntry]:
    """Build provider lookup using precomputed row-index mapping."""
    max_idx = len(_ENTRY_BY_SPECIFICITY)
    return {
        raw_key: _ENTRY_BY_SPECIFICITY[idx - 1]
        for raw_key, idx in row_index.items()
        if 0 < idx <= max_idx
    }


_OPENALEX_LOOKUP: Final[dict[str, PublicationTypeEntry]] = _build_lookup_from_row_index(
    _OPENALEX_ROW_INDEX
)
_CROSSREF_LOOKUP: Final[dict[str, PublicationTypeEntry]] = _build_lookup_from_row_index(
    _CROSSREF_ROW_INDEX
)
_PUBMED_LOOKUP: Final[dict[str, PublicationTypeEntry]] = _build_lookup_from_row_index(
    _PUBMED_ROW_INDEX
)
_S2_LOOKUP: Final[dict[str, PublicationTypeEntry]] = _build_lookup_from_row_index(
    _S2_ROW_INDEX
)

_PROVIDER_LOOKUPS: Final[dict[str, dict[str, PublicationTypeEntry]]] = {
    "openalex": _OPENALEX_LOOKUP,
    "crossref": _CROSSREF_LOOKUP,
    "pubmed": _PUBMED_LOOKUP,
    "semanticscholar": _S2_LOOKUP,
    "semantic_scholar": _S2_LOOKUP,
    "s2": _S2_LOOKUP,
}


def classify_publication_type(
    provider: str,
    raw_type: str | None = None,
    raw_types_list: list[str] | None = None,
) -> PublicationTypeEntry | None:
    """Classify publication type using unified 3-level hierarchy.

    For single-value providers (OpenAlex, CrossRef), ``raw_type`` is used.
    For multi-value providers (PubMed, Semantic Scholar), the most specific
    match from ``raw_types_list`` is returned.
    """

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
