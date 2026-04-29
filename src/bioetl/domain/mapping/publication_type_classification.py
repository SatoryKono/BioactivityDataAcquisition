"""Unified publication type classification for cross-provider harmonization."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.domain.mapping._publication_type_classification_support import (
    canonical_publication_type_key,
    classification_values,
    classify_chembl_type,
    classify_provider_type,
    normalize_publication_classification_value,
    raw_publication_type,
)

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
    "publication_classification_values",
]


@dataclass(frozen=True, slots=True)
class PublicationTypeEntry:
    """Single entry in the unified publication type classification."""

    unified_type: str
    subclass: str
    class_code: str
    specificity: int


_data: ClassificationData | None = None
_ENTRY_BY_SPECIFICITY: list[PublicationTypeEntry] = []
_ENTRY_BY_UNIFIED_TYPE: dict[str, PublicationTypeEntry] = {}
_PROVIDER_LOOKUPS: dict[str, dict[str, PublicationTypeEntry]] = {}


def is_initialized() -> bool:
    """Return whether classification data has been loaded."""
    return bool(_PROVIDER_LOOKUPS)


def get_classification_table_size() -> int:
    """Return the number of entries in the classification table."""
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
            canonical_publication_type_key(entry.unified_type): entry
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
        return classify_chembl_type(
            raw_type=raw_type,
            raw_types_list=raw_types_list,
            entry_by_unified_type=_ENTRY_BY_UNIFIED_TYPE,
        )

    lookup = _get_lookup(provider)
    if lookup is None:
        return None

    return classify_provider_type(
        lookup=lookup,
        raw_type=raw_type,
        raw_types_list=raw_types_list,
    )


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
    raw_value = raw_publication_type(
        raw_type=raw_type,
        raw_types_list=raw_types_list,
    )
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
    return normalize_publication_classification_value(
        field_name=field_name,
        value=value,
        entries=_ENTRY_BY_SPECIFICITY,
    )


def publication_classification_values(field_name: str) -> frozenset[str]:
    """Return allowed values for one derived publication classification field."""
    return classification_values(field_name, _ENTRY_BY_SPECIFICITY)


def _get_lookup(provider: str) -> dict[str, PublicationTypeEntry] | None:
    """Return provider lookup dict, if provider is supported."""
    provider_key = provider.lower()
    if provider_key == "chembl":
        return {}
    return _PROVIDER_LOOKUPS.get(provider_key)
