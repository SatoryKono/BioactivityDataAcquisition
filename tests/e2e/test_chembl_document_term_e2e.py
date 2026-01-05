"""E2E tests for ChEMBL Document Term pipeline.

Tests the complete pipeline execution from fetch to Silver layer.
Uses VCR cassettes for HTTP requests and local file storage.

Document Term is a derived entity that extracts nested term data
from Document API responses and flattens the 1:M relationship.
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
async def test_chembl_document_term_full_cycle(e2e_data_dir: Path):
    """E2E: ChEMBL Document Term pipeline from fetch to Silver.

    Verifies:
    1. Document data is fetched and terms are extracted
    2. Silver table contains expected term records
    3. Each term has required fields
    """
    # Arrange
    ctx = create_test_context("chembl_document_term", limit=5)

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Bronze layer (uses document entity from parent)
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "chembl", "document_term")
    assert len(bronze_files) >= 1

    # Assert - Silver layer
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_document_term", expected_min=1
    )
    assert silver_count >= 1

    # Assert - Schema validation
    records = get_silver_records(e2e_data_dir, "chembl_document_term")
    required_fields = ["document_chembl_id", "term", "term_type"]
    for record in records:
        for field in required_fields:
            assert field in record, f"Missing required field: {field}"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_document_term_types(e2e_data_dir: Path):
    """E2E: Verify term types are correctly classified.

    Document terms can be:
    - MESH_HEADING: MeSH descriptor terms
    - MESH_QUALIFIER: MeSH qualifier/subheading
    - KEYWORD: Author-provided keywords
    """
    # Arrange
    ctx = create_test_context("chembl_document_term", limit=10)

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Check term types
    records = get_silver_records(e2e_data_dir, "chembl_document_term")

    valid_term_types = {"MESH_HEADING", "MESH_QUALIFIER", "KEYWORD", "CONCEPT"}

    for record in records:
        term_type = record.get("term_type")
        assert term_type in valid_term_types, f"Invalid term_type: {term_type}"
        assert record.get("term"), "Term text should not be empty"
        assert record.get("document_chembl_id"), "document_chembl_id should not be empty"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_document_term_mesh_fields(e2e_data_dir: Path):
    """E2E: Verify MeSH-specific fields are extracted.

    MeSH terms may include:
    - mesh_id: MeSH identifier (e.g., "D001241")
    - qualifier: MeSH qualifier (e.g., "pharmacology")
    """
    # Arrange
    ctx = create_test_context("chembl_document_term", limit=10)

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Check MeSH fields presence
    records = get_silver_records(e2e_data_dir, "chembl_document_term")

    mesh_records = [r for r in records if r.get("term_type") in ("MESH_HEADING", "MESH_QUALIFIER")]

    # If there are MeSH records, verify structure
    for record in mesh_records:
        # mesh_id and qualifier may be None, but should exist as keys
        assert "mesh_id" in record or record.get("term_type") == "MESH_QUALIFIER"
