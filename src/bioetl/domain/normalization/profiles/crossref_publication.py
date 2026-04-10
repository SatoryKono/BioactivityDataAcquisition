"""Normalization profile for the CrossRef Publication Silver schema."""

from __future__ import annotations

from bioetl.domain.normalization.profiles._standard_profile_builder import (
    build_standard_profile,
)
from bioetl.infrastructure.schemas.silver_publications import (
    CROSSREF_PUBLICATION_SCHEMA,
)

__all__ = [
    "CROSSREF_PUBLICATION_PROFILE",
    "CROSSREF_PUBLICATION_SCHEMA_FIELDS",
]

CROSSREF_PUBLICATION_SCHEMA_FIELDS = tuple(CROSSREF_PUBLICATION_SCHEMA.names)

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
CROSSREF_PUBLICATION_PROFILE = build_standard_profile(
    profile_name="crossref.publication",
    description="Canonical normalization profile for the CrossRef Publication Silver schema.",
    schema_fields=CROSSREF_PUBLICATION_SCHEMA_FIELDS,
    meta_fields=_META_FIELDS,
    title_fields={"title"},
    abstract_fields={"abstract"},
    doi_fields={"doi"},
    pmid_fields={"pmid"},
    pmc_id_fields={"pmc_id"},
    date_fields={"publication_date", "published", "published_online", "published_print"},
    int_fields={"citations_made", "citations_received", "publication_year"},
    set_like_fields={"subject_keywords"},
)

CROSSREF_PUBLICATION_PROFILE.assert_covers_schema(CROSSREF_PUBLICATION_SCHEMA_FIELDS)
