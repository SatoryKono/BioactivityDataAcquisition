"""Private helpers for unified publication type classification."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol

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
