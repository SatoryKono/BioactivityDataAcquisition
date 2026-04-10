"""Normalization profile for the PubMed Publication Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.infrastructure.schemas.silver_publications import PUBMED_PUBLICATION_SCHEMA

__all__ = [
    "PUBMED_PUBLICATION_PROFILE",
    "PUBMED_PUBLICATION_SCHEMA_FIELDS",
]

PUBMED_PUBLICATION_SCHEMA_FIELDS = tuple(PUBMED_PUBLICATION_SCHEMA.names)

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
PUBMED_PUBLICATION_PROFILE = build_standard_profile(
    profile_name="pubmed.publication",
    description="Canonical normalization profile for the PubMed Publication Silver schema.",
    schema_fields=PUBMED_PUBLICATION_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields={"title"},
    abstract_fields={"abstract"},
    doi_fields={"doi"},
    pmid_fields={"pmid"},
    pmc_id_fields={"pmc_id"},
    date_fields={"date_completed", "date_revised", "pub_date", "publication_date"},
    int_fields={
        "author_count",
        "chemical_count",
        "citations_made",
        "grant_count",
        "keyword_count",
        "mesh_heading_count",
        "pub_day",
        "pub_month",
        "publication_year",
    },
    set_like_fields={"publication_types", "subject_keywords", "subject_mesh"},
)

PUBMED_PUBLICATION_PROFILE.assert_covers_schema(PUBMED_PUBLICATION_SCHEMA_FIELDS)
