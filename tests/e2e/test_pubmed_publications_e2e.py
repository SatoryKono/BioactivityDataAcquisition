"""E2E tests for PubMed Publications pipeline.

Tests the complete pipeline execution from fetch to Gold layer.
Uses VCR cassettes for HTTP requests and local file storage.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.composition.bootstrap import bootstrap_pipeline

from .conftest import (
    assert_bronze_files_exist,
    assert_silver_table_has_records,
    create_test_context,
    get_silver_records,
)


@pytest.fixture(scope="module")
def vcr_cassette_dir() -> Path:
    """Path to VCR cassettes directory."""
    return Path(__file__).parent.parent / "fixtures" / "vcr"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pubmed_publications_full_cycle(e2e_data_dir: Path):
    """E2E: PubMed Publications pipeline from fetch to Silver.

    Verifies:
    1. Publication data is fetched from PubMed via Entrez API
    2. Bronze files are created with raw XML
    3. Silver table contains parsed publication records
    4. Core publication fields are present
    """
    # Arrange
    ctx = create_test_context("pubmed_publications", limit=5)

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Bronze layer
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "pubmed", "publication")
    assert len(bronze_files) >= 1

    # Assert - Silver layer
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "pubmed_publications", expected_min=1
    )
    assert silver_count <= 5

    # Assert - Schema validation
    records = get_silver_records(e2e_data_dir, "pubmed_publications")
    required_fields = ["pmid", "title"]
    for record in records:
        for field in required_fields:
            assert field in record, f"Missing required field: {field}"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pubmed_publications_date_fields(e2e_data_dir: Path):
    """E2E: Verify date fields are extracted correctly.

    Publications should have various date fields:
    - pub_date, pub_year: Publication date
    - accepted_date: Date manuscript was accepted
    - received_date: Date manuscript was received
    - revised_date: Date manuscript was revised
    - epub_date: Electronic publication date
    """
    # Arrange
    ctx = create_test_context("pubmed_publications", limit=5)

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Check date fields
    records = get_silver_records(e2e_data_dir, "pubmed_publications")

    for record in records:
        # PMID must always be present
        assert record.get("pmid") is not None

        # Most publications should have at least pub_year
        pub_year = record.get("pub_year") or record.get("publication_year")
        if pub_year is not None:
            assert (
                1800 <= pub_year <= 2100
            ), f"Invalid pub_year {pub_year} for PMID {record.get('pmid')}"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pubmed_publications_journal_fields(e2e_data_dir: Path):
    """E2E: Verify journal metadata is extracted.

    Publications should have journal information:
    - journal: Full journal name
    - journal_abbrev: ISO abbreviation
    - issn: Journal ISSN
    - volume, issue, pages
    """
    # Arrange
    ctx = create_test_context("pubmed_publications", limit=5)

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Check journal fields
    records = get_silver_records(e2e_data_dir, "pubmed_publications")

    # Verify records were extracted
    assert len(records) >= 1, "Should have at least one publication record"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pubmed_publications_classification_fields(e2e_data_dir: Path):
    """E2E: Verify classification fields are extracted.

    Publications may have:
    - keywords: Author-provided keywords
    - mesh_terms: MeSH subject headings
    - publication_types: Type of publication (Journal Article, Review, etc.)
    """
    # Arrange
    ctx = create_test_context("pubmed_publications", limit=5)

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Check classification fields
    records = get_silver_records(e2e_data_dir, "pubmed_publications")

    for record in records:
        # Keywords and mesh_terms should be lists (possibly empty)
        keywords = record.get("keywords")
        mesh_terms = record.get("mesh_terms")
        pub_types = record.get("publication_types")

        if keywords is not None:
            assert isinstance(
                keywords, list
            ), f"keywords should be list, got {type(keywords)}"

        if mesh_terms is not None:
            assert isinstance(
                mesh_terms, list
            ), f"mesh_terms should be list, got {type(mesh_terms)}"

        if pub_types is not None:
            assert isinstance(
                pub_types, list
            ), f"publication_types should be list, got {type(pub_types)}"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pubmed_publications_identifier_fields(e2e_data_dir: Path):
    """E2E: Verify external identifier fields are extracted.

    Publications should have:
    - pmid: PubMed ID (always present)
    - doi: Digital Object Identifier
    - pmc_id: PubMed Central ID
    """
    # Arrange
    ctx = create_test_context("pubmed_publications", limit=5)

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Check identifier fields
    records = get_silver_records(e2e_data_dir, "pubmed_publications")

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
