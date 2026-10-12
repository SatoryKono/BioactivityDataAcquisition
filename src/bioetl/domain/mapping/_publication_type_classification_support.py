"""Private helpers for unified publication type classification."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from bioetl.domain.mapping.classification_data import ClassificationData
from bioetl.domain.normalization.text import normalize_string


class PublicationTypeEntryProtocol(Protocol):
    """Structural publication-type entry used by helper routines."""

    @property
    def unified_type(self) -> str: ...

    @property
    def subclass(self) -> str: ...

    @property
    def class_code(self) -> str: ...

    @property
    def specificity(self) -> int: ...


def classify_provider_type[PublicationTypeEntryT: PublicationTypeEntryProtocol](
    *,
    lookup: Mapping[str, PublicationTypeEntryT] | None,
    raw_type: str | None,
    raw_types_list: list[str] | None,
) -> PublicationTypeEntryT | None:
    """Resolve a provider-specific publication type from scalar/list inputs."""
    if lookup is None:
        return None
    if raw_type is not None:
        return lookup.get(raw_type.strip().lower())
    if raw_types_list is not None:
        return best_match(lookup, raw_types_list)
    return None


def classify_chembl_type[PublicationTypeEntryT: PublicationTypeEntryProtocol](
    *,
    raw_type: str | None,
    raw_types_list: list[str] | None,
    entry_by_unified_type: Mapping[str, PublicationTypeEntryT],
) -> PublicationTypeEntryT | None:
    """Resolve a ChEMBL publication type using unified-type lookup keys."""
    if raw_type is not None:
        return classify_chembl_publication_type(entry_by_unified_type, raw_type)
    if raw_types_list is not None:
        return best_chembl_match(entry_by_unified_type, raw_types_list)
    return None


def normalize_publication_classification_value(
    *,
    field_name: str,
    value: object,
    entries: Sequence[PublicationTypeEntryProtocol],
) -> object:
    """Normalize a derived publication classification value against loaded entries."""
    if value is None or not isinstance(value, str):
        return None
    normalized = normalize_string(value)
    if normalized is None:
        return None
    allowed = classification_values(field_name, entries)
    if not allowed:
        return normalized
    return find_matching_classification_value(normalized, allowed)


def find_matching_classification_value(
    normalized: str,
    allowed: frozenset[str],
) -> str | None:
    for allowed_value in allowed:
        if normalized.lower() == allowed_value.lower():
            return allowed_value
    return None


def best_match[PublicationTypeEntryT: PublicationTypeEntryProtocol](
    lookup: Mapping[str, PublicationTypeEntryT],
    raw_types: list[str],
) -> PublicationTypeEntryT | None:
    """Return the most specific entry among matching raw types."""
    matches = [
        entry
        for raw in raw_types
        if raw and (entry := lookup.get(raw.strip().lower())) is not None
    ]
    return max(matches, key=lambda entry: entry.specificity, default=None)


_CLASSIFICATION_FIELD_GETTERS = {
    "publication_type_unified": lambda entries: frozenset(
        entry.unified_type for entry in entries
    ),
    "publication_subclass": lambda entries: frozenset(
        entry.subclass for entry in entries
    ),
    "publication_class": lambda entries: frozenset(
        entry.class_code for entry in entries
    ),
}


def classification_values(
    field_name: str,
    entries: Sequence[PublicationTypeEntryProtocol],
) -> frozenset[str]:
    getter = _CLASSIFICATION_FIELD_GETTERS.get(field_name)
    if getter is None:
        raise ValueError(f"Unknown publication classification field: {field_name}")
    return getter(entries)


def raw_publication_type(
    *,
    raw_type: str | None,
    raw_types_list: list[str] | None,
) -> str | None:
    if raw_type is not None:
        stripped = raw_type.strip()
        return stripped or None
    return process_raw_types_list(raw_types_list)


def process_raw_types_list(raw_types_list: list[str] | None) -> str | None:
    if not raw_types_list:
        return None
    processed_parts = [
        part for part in map(_normalized_raw_type_part, raw_types_list) if part
    ]
    return "|".join(processed_parts) if processed_parts else None


def _normalized_raw_type_part(item: object) -> str | None:
    if item is None:
        return None
    stripped = str(item).strip()
    return stripped or None


def canonical_publication_type_key(value: str) -> str:
    from bioetl.domain.mapping.publication_type_mapping import (
        normalize_publication_type,
    )

    return normalize_publication_type(value) or value.strip().lower()


def classify_chembl_publication_type[
    PublicationTypeEntryT: PublicationTypeEntryProtocol
](
    entry_by_unified_type: Mapping[str, PublicationTypeEntryT],
    raw_type: str,
) -> PublicationTypeEntryT | None:
    from bioetl.domain.mapping.publication_type_mapping import (
        normalize_publication_type,
    )

    normalized = normalize_publication_type(raw_type)
    return None if normalized is None else entry_by_unified_type.get(normalized)


def best_chembl_match[PublicationTypeEntryT: PublicationTypeEntryProtocol](
    entry_by_unified_type: Mapping[str, PublicationTypeEntryT],
    raw_types: list[str],
) -> PublicationTypeEntryT | None:
    matches = [
        entry
        for raw in raw_types
        if raw
        and (
            entry := classify_chembl_publication_type(
                entry_by_unified_type,
                raw.strip(),
            )
        )
        is not None
    ]
    return max(matches, key=lambda entry: entry.specificity, default=None)


@dataclass(frozen=True, slots=True)
class PublicationTypeEntry:
    """Single entry in the unified publication type classification."""

    unified_type: str
    subclass: str
    class_code: str
    specificity: int


@dataclass(frozen=True, slots=True)
class _ClassificationViews:
    """Lookup snapshot copied from one ClassificationData object."""

    entries: tuple[PublicationTypeEntry, ...]
    by_unified: dict[str, PublicationTypeEntry]
    lookups: dict[str, dict[str, PublicationTypeEntry]]


_VIEW_CACHE: dict[int, _ClassificationViews] = {}


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


def _views_for(data: ClassificationData) -> _ClassificationViews:
    """Copy one taxonomy object into lookup tables.

    The copy is cached by object identity. Later mutation of the source row
    indexes does not change a snapshot already built from that object.
    """
    cached = _VIEW_CACHE.get(id(data))
    if cached is not None:
        return cached
    entries = tuple(
        PublicationTypeEntry(
            unified_type=unified_type,
            subclass=subclass,
            class_code=class_code,
            specificity=index,
        )
        for index, (unified_type, subclass, class_code) in enumerate(
            data.entry_cores,
            start=1,
        )
    )
    by_unified = {
        canonical_publication_type_key(entry.unified_type): entry for entry in entries
    }
    semantic_scholar = _build_lookup(entries, dict(data.s2_row_index))
    views = _ClassificationViews(
        entries=entries,
        by_unified=by_unified,
        lookups={
            "openalex": _build_lookup(entries, dict(data.openalex_row_index)),
            "crossref": _build_lookup(entries, dict(data.crossref_row_index)),
            "pubmed": _build_lookup(entries, dict(data.pubmed_row_index)),
            "semanticscholar": semantic_scholar,
            "semantic_scholar": semantic_scholar,
            "s2": semantic_scholar,
        },
    )
    _VIEW_CACHE[id(data)] = views
    return views


def _require_classification_data(
    data: ClassificationData | None,
) -> ClassificationData:
    if data is None:
        raise RuntimeError("publication classification data must be passed explicitly")
    return data


def refresh_classification_views(data: ClassificationData) -> _ClassificationViews:
    """Drop the cached snapshot for this object and rebuild it."""

    _VIEW_CACHE.pop(id(data), None)
    return _views_for(data)
