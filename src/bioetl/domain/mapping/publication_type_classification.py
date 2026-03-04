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
    CLASSIFICATION_TABLE_SIZE,
)

__all__ = [
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


_DASH = "—"


def _build_lookups() -> tuple[
    dict[str, PublicationTypeEntry],
    dict[str, PublicationTypeEntry],
    dict[str, PublicationTypeEntry],
    dict[str, PublicationTypeEntry],
]:
    """Build provider-specific lookup dictionaries.

    Keys are normalized to lowercase. If a key ends with ``*`` in source CSV,
    it is treated as an additional (secondary) alias and does not override a
    primary key already registered earlier.
    """

    openalex: dict[str, PublicationTypeEntry] = {}
    crossref: dict[str, PublicationTypeEntry] = {}
    pubmed: dict[str, PublicationTypeEntry] = {}
    s2: dict[str, PublicationTypeEntry] = {}

    for row_idx, row in enumerate(_CLASSIFICATION_TABLE, start=1):
        unified_type, subclass, class_code, oa_keys, cr_keys, pm_keys, s2_keys = row
        entry = PublicationTypeEntry(
            unified_type=unified_type,
            subclass=subclass,
            class_code=class_code,
            specificity=row_idx,
        )

        for raw_key, target in (
            (oa_keys, openalex),
            (cr_keys, crossref),
            (pm_keys, pubmed),
            (s2_keys, s2),
        ):
            if raw_key == _DASH:
                continue
            key = raw_key.rstrip("*").lower()
            if key not in target:
                target[key] = entry

    return openalex, crossref, pubmed, s2


_OPENALEX_LOOKUP, _CROSSREF_LOOKUP, _PUBMED_LOOKUP, _S2_LOOKUP = _build_lookups()

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
