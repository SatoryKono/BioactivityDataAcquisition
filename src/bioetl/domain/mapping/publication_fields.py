"""Publication field mapping for cross-provider unification.

Provides bidirectional mapping between provider-specific field names
and unified canonical names for publication entities across ChEMBL,
CrossRef, OpenAlex, PubMed, and SemanticScholar.

Rationale (ADR-029: Output Metadata Unification):
- Eliminates semantic duplication (doc_type vs source_type, year vs publication_year)
- Enables seamless composite pipeline aggregation
- Maintains backward compatibility via field_aliases in YAML configs
- Follows principle: "Uniform interface, diverse implementations"

Usage:
    >>> from bioetl.domain.mapping import PUBLICATION_FIELD_MAPPING
    >>> mapping = PUBLICATION_FIELD_MAPPING["chembl"]
    >>> mapping["doc_type"]  # Returns: "publication_type"

    >>> from bioetl.domain.mapping import get_unified_name
from bioetl.domain.types import JsonDict
    >>> get_unified_name("chembl", "year")  # Returns: "publication_year"
"""

from __future__ import annotations

from typing import Final, Literal

from bioetl.domain.types import JsonDict

__all__ = [
    "ProviderName",
    "apply_field_mapping",
    "get_provider_name",
    "get_unified_name",
]


# Provider type for type safety
ProviderName = Literal["chembl", "crossref", "openalex", "pubmed", "semanticscholar"]


# ============================================================================
# PROVIDER → UNIFIED MAPPINGS
# ============================================================================

_CHEMBL_MAPPING: Final[dict[str, str]] = {
    # Document type
    "doc_type": "publication_type",
    # Temporal fields
    "year": "publication_year",
    # Note: ChEMBL uses 'journal' (already canonical)
    # Note: ChEMBL uses 'abstract' (already canonical)
}

_CROSSREF_MAPPING: Final[dict[str, str]] = {
    # Document type
    "source_type": "publication_type",
    # Temporal fields
    "year": "publication_year",
    # Journal fields
    "short_container_title": "journal_name_short",
    # Pagination
    "first_page": "page_first",
    "last_page": "page_last",
    # Citations
    "citation_count": "citations_received",
    "reference_count": "citations_made",
    # Subjects (generic)
    "subjects": "subject_keywords",
}

_OPENALEX_MAPPING: Final[dict[str, str]] = {
    # Document type
    "source_type": "publication_type",
    # Temporal fields
    "year": "publication_year",
    # Journal name (OpenAlex uses 'journal' - already canonical)
    # Pagination
    "first_page": "page_first",
    "last_page": "page_last",
    # Citations
    "citation_count": "citations_received",
    "reference_count": "citations_made",
    # Subjects
    "topics": "subject_topics",
    "keywords": "subject_keywords",
    # Affiliations
    "affiliations": "affiliation_list",
}

_PUBMED_MAPPING: Final[dict[str, str]] = {
    # Temporal fields
    "year": "publication_year",
    # Journal fields (canonicalize to unified names)
    "journal_title": "journal",
    "journal_abbrev": "journal_name_short",
    # Pagination
    "first_page": "page_first",
    "last_page": "page_last",
    "pages": "page_range",
    # Citations
    "reference_count": "citations_made",
    # Subjects
    "keywords": "subject_keywords",
    "mesh_terms": "subject_mesh",
    # Affiliations
    "affiliations": "affiliation_list",
    "structured_affiliations": "affiliation_structured",
}

_SEMANTICSCHOLAR_MAPPING: Final[dict[str, str]] = {
    # Document type
    # Note: SemanticScholar doesn't have doc_type - inferred from venue/journal
    # Temporal fields
    "year": "publication_year",
    # Pagination
    "first_page": "page_first",
    "last_page": "page_last",
    "pages": "page_range",
    # Citations
    "citation_count": "citations_received",
    "reference_count": "citations_made",
    # Subjects
    "fields_of_study": "subject_fields",
    # Affiliations
    "affiliations": "affiliation_list",
}


# Aggregate mapping: Provider → Old Field → New Field
PUBLICATION_FIELD_MAPPING: Final[dict[ProviderName, dict[str, str]]] = {
    "chembl": _CHEMBL_MAPPING,
    "crossref": _CROSSREF_MAPPING,
    "openalex": _OPENALEX_MAPPING,
    "pubmed": _PUBMED_MAPPING,
    "semanticscholar": _SEMANTICSCHOLAR_MAPPING,
}


# ============================================================================
# UNIFIED → PROVIDER MAPPINGS (Reverse mapping for backward compatibility)
# ============================================================================


def _build_reverse_mapping() -> dict[ProviderName, dict[str, str]]:
    """Build reverse mapping: Provider → Unified → Original."""
    reverse: dict[ProviderName, dict[str, str]] = {}
    for provider, mapping in PUBLICATION_FIELD_MAPPING.items():
        reverse[provider] = {unified: original for original, unified in mapping.items()}
    return reverse


UNIFIED_TO_PROVIDER: Final[dict[ProviderName, dict[str, str]]] = (
    _build_reverse_mapping()
)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def get_unified_name(provider: ProviderName, field_name: str) -> str:
    """Get unified field name for a provider-specific field.

    Args:
        provider: Provider name (chembl, crossref, openalex, pubmed, semanticscholar).
        field_name: Provider-specific field name.

    Returns:
        Unified field name. If no mapping exists, returns the original field_name.

    Example:
        >>> get_unified_name("chembl", "doc_type")
        "publication_type"
        >>> get_unified_name("chembl", "title")  # No mapping needed
        "title"
    """
    mapping = PUBLICATION_FIELD_MAPPING.get(provider, {})
    return mapping.get(field_name, field_name)


def get_provider_name(provider: ProviderName, unified_field: str) -> str:
    """Get provider-specific field name for a unified field (reverse lookup).

    Args:
        provider: Provider name.
        unified_field: Unified field name.

    Returns:
        Provider-specific field name. If no mapping exists, returns unified_field.

    Example:
        >>> get_provider_name("chembl", "publication_type")
        "doc_type"
        >>> get_provider_name("chembl", "title")  # No mapping needed
        "title"
    """
    mapping = UNIFIED_TO_PROVIDER.get(provider, {})
    return mapping.get(unified_field, unified_field)


def apply_field_mapping(
    record: JsonDict,
    provider: ProviderName,
) -> JsonDict:
    """Apply field name mapping to a record (provider → unified names).

    Renames fields according to PUBLICATION_FIELD_MAPPING for the given provider.
    Fields not in mapping are preserved as-is.

    Args:
        record: Record dictionary with provider-specific field names.
        provider: Provider name.

    Returns:
        New dictionary with unified field names.

    Example:
        >>> record = {"doc_type": "article", "year": 2020, "title": "Test"}
        >>> apply_field_mapping(record, "chembl")
        {"publication_type": "article", "publication_year": 2020, "title": "Test"}
    """
    mapping = PUBLICATION_FIELD_MAPPING.get(provider, {})
    result: dict[str, object] = {}

    for key, value in record.items():
        # Map to unified name if mapping exists, otherwise keep original
        unified_key = mapping.get(key, key)
        if unified_key in result:
            raise ValueError(
                "publication field mapping produced a duplicate unified key "
                f"{unified_key!r} from {key!r}"
            )
        result[unified_key] = value

    return result


# ============================================================================
# UNIFIED FIELD CATALOG (Documentation)
# ============================================================================

# Canonical unified field names (for reference):
#
# IDENTIFIERS:
#   - doi, pmid (already unified across providers)
#   - Provider-specific IDs kept as-is (document_chembl_id, openalex_id, etc.)
#
# CORE METADATA:
#   - title (unified)
#   - abstract (unified)
#   - publication_type (was: doc_type in ChEMBL, source_type in CrossRef/OpenAlex)
#
# AUTHORS & AFFILIATIONS:
#   - authors (unified)
#   - author_orcids (unified structure for ORCID identifiers)
#   - affiliation_list (unified, was: affiliations in all)
#   - affiliation_structured (PubMed-specific structured data)
#
# JOURNAL:
#   - journal_name (was: journal in most, journal_title in PubMed)
#   - journal_name_short (was: short_container_title in CrossRef, journal_abbrev in PubMed)
#   - issn (unified)
#
# TEMPORAL:
#   - publication_year (was: year in all)
#   - publication_date (unified)
#
# PAGINATION:
#   - page_first (was: first_page)
#   - page_last (was: last_page)
#   - page_range (was: pages in PubMed/SemanticScholar)
#   - volume, issue (unified)
#
# CITATIONS:
#   - citations_received (was: citation_count)
#   - citations_made (was: reference_count)
#
# SUBJECTS & CLASSIFICATION:
#   - subject_keywords (was: subjects in CrossRef, keywords in others)
#   - subject_mesh (was: mesh_terms)
#   - subject_topics (was: topics in OpenAlex)
#   - subject_fields (was: fields_of_study in SemanticScholar)
#
# OPEN ACCESS:
#   - is_oa (unified)
#   - oa_status (unified)
#
# MISCELLANEOUS:
#   - publisher (unified)
#   - language (unified)
