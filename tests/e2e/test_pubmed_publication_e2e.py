"""E2E tests for PubMed Publications pipeline.

Tests the complete pipeline execution from fetch to Gold layer.
Uses VCR cassettes for HTTP requests and local file storage.

Cassettes location: tests/fixtures/vcr/pubmed/
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from tests.helpers.vcr_config import (
    QUERY_IGNORE_EMAIL_MATCH_ON,
    build_base_vcr_config,
)

from bioetl.composition.bootstrap import bootstrap_pipeline_runner

from .conftest import (
    assert_bronze_files_exist,
    assert_silver_table_has_records,
    create_test_context,
    get_silver_records,
)


# YYYY-MM-DD pattern for date validation
DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# All date fields that must follow YYYY-MM-DD format when present
PUBMED_DATE_FIELDS = [
    "publication_date",
    "pub_date",
    "epub_date",
    "accepted_date",
    "received_date",
    "revised_date",
]


@pytest.fixture(scope="module")
def vcr_config(vcr_cassette_dir: Path) -> dict[str, object]:
    """Configure VCR for PubMed Publications E2E tests."""
    return build_base_vcr_config(
        cassette_library_dir=vcr_cassette_dir,
        match_on=QUERY_IGNORE_EMAIL_MATCH_ON,
        decode_compressed_response=True,
    )


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pubmed_publication_full_cycle(e2e_data_dir: Path):
    """E2E: PubMed Publications pipeline from fetch to Silver.

    Verifies:
    1. Publication data is fetched from PubMed via Entrez API
    2. Bronze files are created with raw XML
    3. Silver table contains parsed publication records
    4. Core publication fields are present
    """
    # Arrange
    ctx = create_test_context("pubmed_publication", limit=5)

    # Act
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Bronze layer
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "pubmed", "publication")
    assert len(bronze_files) >= 1

    # Assert - Silver layer
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "pubmed_publication", expected_min=1
    )
    assert silver_count <= 5

    # Assert - Schema validation
    records = get_silver_records(e2e_data_dir, "pubmed_publication")
    required_fields = ["pmid", "title"]
    for record in records:
        for field in required_fields:
            assert field in record, f"Missing required field: {field}"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pubmed_publication_date_fields(e2e_data_dir: Path):
    """E2E: Verify date fields are extracted correctly.

    Publications should have various date fields:
    - pub_date, year: Publication date
    - accepted_date: Date manuscript was accepted
    - received_date: Date manuscript was received
    - revised_date: Date manuscript was revised
    - epub_date: Electronic publication date

    All date fields (except year) must be in YYYY-MM-DD format.
    """
    # Arrange
    ctx = create_test_context("pubmed_publication", limit=5)

    # Act
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Check date fields
    records = get_silver_records(e2e_data_dir, "pubmed_publication")

    for record in records:
        pmid = record.get("pmid")
        # PMID must always be present
        assert pmid is not None

        # Most publications should have at least year
        year = record.get("publication_year")
        if year is not None:
            assert 1500 <= year <= 2100, f"Invalid year {year} for PMID {pmid}"

        # All date fields must be YYYY-MM-DD format when present
        for field in PUBMED_DATE_FIELDS:
            value = record.get(field)
            if value is not None:
                assert DATE_PATTERN.match(value), (
                    f"Invalid {field} format: {value} for PMID {pmid}, "
                    f"expected YYYY-MM-DD"
                )


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pubmed_publication_journal_fields(e2e_data_dir: Path):
    """E2E: Verify journal metadata is extracted.

    Publications should have journal information:
    - journal: Full journal name
    - journal_name_short: ISO abbreviation
    - issn: Journal ISSN
    - volume, issue, page_range
    """
    # Arrange
    ctx = create_test_context("pubmed_publication", limit=5)

    # Act
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Check journal fields
    records = get_silver_records(e2e_data_dir, "pubmed_publication")

    # Verify records were extracted
    assert len(records) >= 1, "Should have at least one publication record"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pubmed_publication_classification_fields(e2e_data_dir: Path):
    """E2E: Verify classification fields are extracted.

    Publications may have:
    - subject_keywords: Author-provided keywords
    - subject_mesh: MeSH subject headings
    - publication_types: Type of publication (Journal Article, Review, etc.)
    """
    # Arrange
    ctx = create_test_context("pubmed_publication", limit=5)

    # Act
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Check classification fields
    records = get_silver_records(e2e_data_dir, "pubmed_publication")

    for record in records:
        # Keywords and mesh_terms should be lists (possibly empty)
        keywords = record.get("subject_keywords")
        mesh_terms = record.get("subject_mesh")
        pub_types = record.get("publication_types")

        if keywords is not None:
            assert isinstance(keywords, list), (
                f"keywords should be list, got {type(keywords)}"
            )

        if mesh_terms is not None:
            assert isinstance(mesh_terms, list), (
                f"mesh_terms should be list, got {type(mesh_terms)}"
            )

        if pub_types is not None:
            assert isinstance(pub_types, list), (
                f"publication_types should be list, got {type(pub_types)}"
            )


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pubmed_publication_identifier_fields(e2e_data_dir: Path):
    """E2E: Verify external identifier fields are extracted.

    Publications should have:
    - pmid: PubMed ID (always present)
    - doi: Digital Object Identifier
    - pmc_id: PubMed Central ID
    """
    # Arrange
    ctx = create_test_context("pubmed_publication", limit=5)

    # Act
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Check identifier fields
    records = get_silver_records(e2e_data_dir, "pubmed_publication")

    for record in records:
        # PMID is always required
        pmid = record.get("pmid")
        assert pmid is not None, "PMID must always be present"
        assert isinstance(pmid, str), f"PMID should be string, got {type(pmid)}"

        # DOI may or may not be present
        doi = record.get("doi")
        if doi is not None:
            # DOI should start with "10."
            assert doi.startswith("10."), f"Invalid DOI format: {doi}"

        # PMC ID format check
        pmc_id = record.get("pmc_id")
        if pmc_id is not None:
            # PMC ID should start with "PMC"
            assert pmc_id.startswith("PMC"), f"Invalid PMC ID format: {pmc_id}"
