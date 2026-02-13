import os
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlparse

import pandas as pd
import pytest
import vcr as vcrpy
from hypothesis import settings

# --- Hypothesis Configuration ---
# Profiles defined in docs/03-guides/testing.md
# ci: max_examples=10
# fast: max_examples=5
# dev: max_examples=50 (default)
# thorough: max_examples=200

settings.register_profile("ci", max_examples=10)
settings.register_profile("fast", max_examples=5)
settings.register_profile("dev", max_examples=50)
settings.register_profile("thorough", max_examples=200)

# Load profile from env or default to 'dev'
profile = os.getenv("HYPOTHESIS_PROFILE", "dev")
settings.load_profile(profile)


@pytest.fixture(scope="session", autouse=True)
def default_vcr_record_mode() -> None:
    """Set deterministic default VCR mode for local runs.

    - CI remains strict (`none`) to prevent silent cassette rewrites.
    - Local runs default to `once` to allow recording missing interactions.
    - Explicit VCR_RECORD_MODE always has priority.
    """
    if "VCR_RECORD_MODE" in os.environ:
        return

    os.environ["VCR_RECORD_MODE"] = "none" if os.getenv("CI") else "once"


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Return repository root for path-based architecture checks."""
    return Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def src_dir(project_root: Path) -> Path:
    """Return the `src` directory used by architecture tests."""
    src_path = project_root / "src"
    if not src_path.exists():
        pytest.skip("Source directory not found: src")
    return src_path


@pytest.fixture(scope="session")
def pyproject_toml(project_root: Path) -> Path:
    """Return path to pyproject.toml."""
    return project_root / "pyproject.toml"


@pytest.fixture
def isolated_registry() -> Any:
    """Return a fresh pipeline registry instance for test isolation."""
    from bioetl.composition.registry import create_registry

    return create_registry()


@pytest.fixture
def populated_isolated_registry(isolated_registry: Any) -> Any:
    """Return isolated registry pre-populated with all pipelines."""
    from bioetl.composition.factories.pipeline_factories import register_all_pipelines

    register_all_pipelines(registry=isolated_registry)
    return isolated_registry


# --- VCR Configuration ---
@pytest.fixture(scope="module")
def vcr_config() -> dict[str, object]:
    """VCR configuration for integration tests."""
    return {
        "filter_headers": ["authorization", "x-api-key", "cookie"],
        "filter_query_parameters": ["api_key", "key"],
        "ignore_localhost": True,
        "record_mode": "once",
    }


def _strip_email_query(uri: str) -> list[tuple[str, str]]:
    """Return query params excluding email for VCR matching."""
    query_params = parse_qsl(urlparse(uri).query, keep_blank_values=True)
    return [(key, value) for key, value in query_params if key.lower() != "email"]


def query_ignore_email(request_1: Any, request_2: Any) -> bool:
    """Custom VCR matcher that ignores email query parameter."""
    return _strip_email_query(request_1.uri) == _strip_email_query(request_2.uri)


@pytest.fixture(scope="module")
def vcr(vcr_config: dict[str, object]) -> Any:  # type: ignore[override]
    """Configure VCR instance with custom matchers."""
    vcr_instance = vcrpy.VCR(**vcr_config)
    vcr_instance.register_matcher("query_ignore_email", query_ignore_email)
    return vcr_instance


@pytest.fixture
def noop_logger():
    """Minimal no-op logger for tests."""
    from bioetl.infrastructure.observability.noop_logger import NoOpLogger

    return NoOpLogger()


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
    data = dict.fromkeys(all_cols)

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

    # Use PUBLICATION for ChEMBL, journal-article for others to satisfy enums
    if provider == "chembl":
        data["publication_type"] = "PUBLICATION"
    else:
        data["publication_type"] = "journal-article"

    # Set PK
    data[pk_field] = pk_value

    return pd.DataFrame([data])


@pytest.fixture
def minimal_pubmed_publication_df():
    df = _create_minimal_df(
        PUBMED_SPECIFIC, "pubmed", "pubmed_12345678", "pmid", "12345678"
    )
    df["abstract_structured"] = False
    # Fix for TestPublicationTypeValid::test_pub_type_present
    df["publication_type"] = "Journal Article"
    return df


@pytest.fixture
def minimal_chembl_publication_df():
    df = _create_minimal_df(
        CHEMBL_SPECIFIC, "chembl", "CHEMBL123", "publication_id", "CHEMBL123"
    )
    df["publication_type"] = "PUBLICATION"
    return df


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
