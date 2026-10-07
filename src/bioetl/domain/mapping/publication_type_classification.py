"""Unified publication type classification for cross-provider harmonization.

This module governs only the derived taxonomy-backed fields:
``publication_type_unified``, ``publication_subclass``, and
``publication_class``.

Raw provider-native labels remain provider sidecars. Unknown raw values are
preserved in the raw field and do not implicitly become accepted taxonomy
members.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.mapping._publication_type_classification_support import (
    PublicationTypeEntry as PublicationTypeEntry,
)
from bioetl.domain.mapping._publication_type_classification_support import (
    _require_classification_data,
    _views_for,
    classification_values,
    classify_chembl_type,
    classify_provider_type,
    normalize_publication_classification_value,
    raw_publication_type,
    refresh_classification_views,
)

if TYPE_CHECKING:
    from bioetl.domain.mapping.classification_data import ClassificationData

__all__ = [
    "PublicationTypeEntry",
    "build_publication_type_classification_payload",
    "classification_install",
    "classify_publication_type",
    "get_classification_table_size",
    "initialize_classification",
    "is_initialized",
    "normalize_publication_classification_field",
    "publication_classification_values",
]


_data: ClassificationData | None = None
_ENTRY_BY_SPECIFICITY: list[PublicationTypeEntry] = []
_ENTRY_BY_UNIFIED_TYPE: dict[str, PublicationTypeEntry] = {}
_PROVIDER_LOOKUPS: dict[str, dict[str, PublicationTypeEntry]] = {}


class ClassificationInstall:
    """Taxonomy object installed for fixed-signature schema, DQ, and profile seams."""

    __slots__ = ("data",)

    def __init__(self) -> None:
        self.data: ClassificationData | None = None


classification_install = ClassificationInstall()


def is_initialized() -> bool:
    """Return whether classification data has been loaded."""
    return bool(_PROVIDER_LOOKUPS)


def get_classification_table_size() -> int:
    """Return the number of entries in the classification table."""
    return len(_ENTRY_BY_SPECIFICITY)


def initialize_classification(data: ClassificationData) -> None:
    """Install classification lookups from one loaded taxonomy object.

    Safe to call multiple times. Containers are mutated in-place so that
    references obtained via ``from … import _PROVIDER_LOOKUPS`` at module
    collection time see the populated data. Production classifiers do not
    read those containers; callers pass ``data``.

    Args:
        data: ClassificationData loaded from the JSON asset file.
    """
    global _data

    _data = data
    classification_install.data = data
    views = refresh_classification_views(data)
    _ENTRY_BY_SPECIFICITY.clear()
    _ENTRY_BY_SPECIFICITY.extend(views.entries)
    _ENTRY_BY_UNIFIED_TYPE.clear()
    _ENTRY_BY_UNIFIED_TYPE.update(views.by_unified)
    _PROVIDER_LOOKUPS.clear()
    _PROVIDER_LOOKUPS.update(views.lookups)


def classify_publication_type(
    provider: str,
    raw_type: str | None = None,
    raw_types_list: list[str] | None = None,
    *,
    data: ClassificationData | None = None,
) -> PublicationTypeEntry | None:
    """Classify publication type using unified 3-level hierarchy.

    For single-value providers (OpenAlex, CrossRef), ``raw_type`` is used.
    For multi-value providers (PubMed, Semantic Scholar), the most specific
    match from ``raw_types_list`` is returned.

    Args:
        provider: Provider name (e.g., 'openalex', 'pubmed', 'crossref', 'semanticscholar').
        raw_type: Single raw type string for single-value providers. Defaults to None.
        raw_types_list: List of raw type strings for multi-value providers. Defaults to None.
        data: Taxonomy object for this call. Required.

    Returns:
        PublicationTypeEntry if a match is found, None if provider is unknown
        or no match is found.

    Raises:
        RuntimeError: If ``data`` is omitted.
    """
    taxonomy = _require_classification_data(data)
    views = _views_for(taxonomy)
    provider_lower = provider.lower()
    if provider_lower == "chembl":
        return classify_chembl_type(
            raw_type=raw_type,
            raw_types_list=raw_types_list,
            entry_by_unified_type=views.by_unified,
        )

    lookup = views.lookups.get(provider_lower)
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
    data: ClassificationData | None = None,
) -> dict[str, str | None]:
    """Build the raw-provider and unified classification payload.

    The default raw field is intentionally named ``publication_type_raw`` for
    callers that need an explicit sidecar field. Existing Silver schemas use
    ``publication_type`` for the same raw value and pass that name explicitly.
    Unknown raw provider values remain preserved in that raw field while the
    derived taxonomy fields fail closed to ``None``.
    """
    raw_value = raw_publication_type(
        raw_type=raw_type,
        raw_types_list=raw_types_list,
    )
    entry = classify_publication_type(
        provider,
        raw_type=raw_type,
        raw_types_list=raw_types_list,
        data=data,
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


def normalize_publication_classification_field(
    field_name: str,
    value: object,
    *,
    data: ClassificationData | None = None,
) -> object:
    """Normalize derived publication classification fields against one taxonomy object.

    ``data=None`` keeps the pre-install behavior: known fields are string-normalized
    and unknown field names still fail closed.
    """
    entries = () if data is None else _views_for(data).entries
    return normalize_publication_classification_value(
        field_name=field_name,
        value=value,
        entries=entries,
    )


def publication_classification_values(
    field_name: str,
    data: ClassificationData,
) -> frozenset[str]:
    """Return allowed values for one derived publication classification field."""
    return classification_values(field_name, _views_for(data).entries)


def _get_lookup(provider: str) -> dict[str, PublicationTypeEntry] | None:
    """Return provider lookup dict, if provider is supported."""
    provider_key = provider.lower()
    if provider_key == "chembl":
        return {}
    return _PROVIDER_LOOKUPS.get(provider_key)
