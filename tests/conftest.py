import os
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlparse
from datetime import datetime

import pandas as pd
import numpy as np
from hypothesis import settings
import pytest
import vcr as vcrpy

# --- Hypothesis Configuration ---
...
@pytest.fixture(scope="module")
def vcr(vcr_config: dict[str, object]) -> Any:  # type: ignore[override]
    """Configure VCR instance with custom matchers."""
    vcr_instance = vcrpy.VCR(**vcr_config)
    vcr_instance.register_matcher("query_ignore_email", query_ignore_email)
    return vcr_instance


# --- Publication Fixtures (Minimal DataFrames for Validation) ---

# Columns from ETLRecordSchema (with aliases)
SYSTEM_COLUMNS = [
    "entity_id",
    "content_hash",
    "_run_id",
    "_run_type",
    "_source_batch_id",
    "_ingestion_ts",
    "_dq_warn",
    "_dq_error",
    "_index",
]

# Columns from PublicationBaseSchema (including aliases like _lookup_method)
BASE_PUBLICATION_COLUMNS = [
    "pmid",
    "doi",
    "pmc_id",
    "title",
    "abstract",
    "authors",
    "affiliation_list",
    "author_orcids",
    "author_ormolecule_ids",
    "journal",
    "publication_year",
    "publication_date",
    "publication_type",
    "publication_type_unified",
    "publication_subclass",
    "publication_class",
    "language",
    "page_first",
    "page_last",
    "citations_received",
    "citations_made",
    "is_oa",
    "_lookup_method",
    "_original_id",
    "_source",
]

PUBMED_SPECIFIC = [
    "pii",
    "mid",
    "publisher_id",
    "abstract_structured",
    "journal_name_short",
    "journal_iso_abbrev",
    "issn",
    "journal_issn_type",
    "nlm_unique_id",
    "country",
    "medline_pgn",
    "page_range",
    "pub_month",
    "pub_day",
    "publication_status",
    "publication_type_list",
    "date_completed",
    "date_revised",
    "citation_subset",
    "affiliation_structured",
    "author_count",
    "mesh_heading_count",
    "keyword_count",
    "grant_count",
    "chemical_count",
    "subject_mesh",
    "chemicals",
    "subject_keywords",
    "databanks",
    "gene_symbols",
    "publication_types",
    "authors_with_affiliations",
]

CHEMBL_SPECIFIC = [
    "publication_id",
    "src_id",
    "chembl_release",
    "creation_date",
    "volume",
    "issue",
]

SEMANTIC_SCHOLAR_SPECIFIC = [
    "paper_id",
    "dblp_id",
    "corpus_id",
    "tldr",
    "volume",
    "page_range",
    "influential_citation_count",
    "open_access_url",
    "oa_status",
    "subject_fields",
    "publication_types",
    "author_s2_ids",
    "author_h_indices",
    "citation_contexts",
]

OPENALEX_SPECIFIC = [
    "openalex_id",
    "issn",
    "publisher",
    "oa_status",
    "volume",
    "issue",
    "fwci",
    "is_retracted",
    "subject_topics",
    "primary_topic",
    "grants",
    "subject_mesh",
    "subject_keywords",
    "mag_id",
    "author_openalex_ids",
    "institution_ids",
    "institution_country_codes",
    "ror_ids",
]

CROSSREF_SPECIFIC = [
    "issn",
    "issn_list",
    "publisher",
    "published_print",
    "published_online",
    "license_url",
    "subject_keywords",
    "content_domain_domains",
    "content_domain_crossmark_restriction",
    "alternative_id",
    "published",
    "journal_name_short",
    "issn_print",
    "issn_electronic",
    "author_details",
    "references",
]


def _create_minimal_df(columns, provider, entity_id, pk_field, pk_value):
    all_cols = list(set(SYSTEM_COLUMNS + BASE_PUBLICATION_COLUMNS + columns))
    data = {col: None for col in all_cols}

    # Set required system fields
    data["entity_id"] = entity_id
    data["content_hash"] = "a" * 64
    data["_run_id"] = "test_run"
    data["_run_type"] = "incremental"
    data["_ingestion_ts"] = "2024-01-15T10:30:00Z"
    data["_index"] = 0
    data["_dq_warn"] = False
    data["_dq_error"] = False

    # Set required base fields
    data["_source"] = provider
    data["_lookup_method"] = "direct"
    data["title"] = f"Minimal {provider} Publication"

    # Set PK
    data[pk_field] = pk_value

    return pd.DataFrame([data])


@pytest.fixture
def minimal_pubmed_publication_df():
    df = _create_minimal_df(
        PUBMED_SPECIFIC, "pubmed", "pubmed_12345678", "pmid", "12345678"
    )
    df["abstract_structured"] = False
    return df


@pytest.fixture
def minimal_chembl_publication_df():
    return _create_minimal_df(
        CHEMBL_SPECIFIC, "chembl", "CHEMBL123", "publication_id", "CHEMBL123"
    )


@pytest.fixture
def minimal_semanticscholar_publication_df():
    return _create_minimal_df(
        SEMANTIC_SCHOLAR_SPECIFIC,
        "semanticscholar",
        "s2_" + "a" * 40,
        "paper_id",
        "a" * 40,
    )


@pytest.fixture
def minimal_openalex_publication_df():
    df = _create_minimal_df(
        OPENALEX_SPECIFIC, "openalex", "W12345678", "openalex_id", "W12345678"
    )
    df["is_retracted"] = False
    return df


@pytest.fixture
def minimal_crossref_publication_df():
    return _create_minimal_df(
        CROSSREF_SPECIFIC, "crossref", "10.1001/test", "doi", "10.1001/test"
    )
