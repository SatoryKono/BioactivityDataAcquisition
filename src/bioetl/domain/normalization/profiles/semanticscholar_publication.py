"""Normalization profile for the Semantic Scholar Publication Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.infrastructure.schemas.silver_publications import (
    SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
)

__all__ = [
    "SEMANTICSCHOLAR_PUBLICATION_PROFILE",
    "SEMANTICSCHOLAR_PUBLICATION_SCHEMA_FIELDS",
]

SEMANTICSCHOLAR_PUBLICATION_SCHEMA_FIELDS = tuple(
    SEMANTICSCHOLAR_PUBLICATION_SCHEMA.names
)

_META_FIELDS = frozenset(
    {
        "entity_id",
        "content_hash",
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_source",
        "_ingestion_ts",
        "_index",
        "_lookup_method",
        "_original_id",
        "_dq_error",
        "_dq_warn",
    }
)
_TITLE_FIELDS = frozenset({"title"})
_ABSTRACT_FIELDS = frozenset({"abstract", "tldr"})
_DOI_FIELDS = frozenset({"doi"})
_PMID_FIELDS = frozenset({"pmid"})
_PMC_ID_FIELDS = frozenset({"pmc_id"})
_DATE_FIELDS = frozenset({"publication_date"})
_INT_FIELDS = frozenset(
    {
        "citations_made",
        "citations_received",
        "corpus_id",
        "influential_citation_count",
        "publication_year",
    }
)

SEMANTICSCHOLAR_PUBLICATION_PROFILE = build_standard_profile(
    profile_name="semanticscholar.publication",
    description="Canonical field-level normalization policy for the Semantic Scholar Publication Silver schema.",
    schema_fields=SEMANTICSCHOLAR_PUBLICATION_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields=_TITLE_FIELDS,
    abstract_fields=_ABSTRACT_FIELDS,
    doi_fields=_DOI_FIELDS,
    pmid_fields=_PMID_FIELDS,
    pmc_id_fields=_PMC_ID_FIELDS,
    date_fields=_DATE_FIELDS,
    int_fields=_INT_FIELDS,
)

SEMANTICSCHOLAR_PUBLICATION_PROFILE.assert_covers_schema(
    SEMANTICSCHOLAR_PUBLICATION_SCHEMA_FIELDS
)
