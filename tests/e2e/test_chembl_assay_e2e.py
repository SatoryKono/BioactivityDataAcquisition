"""E2E tests for ChEMBL Assay pipeline.

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
async def test_chembl_assay_full_cycle(e2e_data_dir: Path):
    """E2E: ChEMBL Assay pipeline from fetch to Silver.

    Verifies:
    1. Assay data is fetched and transformed
    2. Silver table contains expected records
    3. Core assay fields are present
    """
    # Arrange
    ctx = create_test_context("chembl_assay", limit=5)

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Bronze layer
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "chembl", "assay")
    assert len(bronze_files) >= 1

    # Assert - Silver layer
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_assay", expected_min=1
    )
    assert silver_count <= 5

    # Assert - Schema validation
    records = get_silver_records(e2e_data_dir, "chembl_assay")
    required_fields = ["assay_chembl_id", "assay_type"]
    for record in records:
        for field in required_fields:
            assert field in record, f"Missing required field: {field}"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_assay_metadata_fields(e2e_data_dir: Path):
    """E2E: Verify assay metadata fields are extracted.

    Assays should have type, description, and target information when available.
    """
    # Arrange
    ctx = create_test_context("chembl_assay", limit=5)

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Check metadata fields
    records = get_silver_records(e2e_data_dir, "chembl_assay")

    for record in records:
        # assay_chembl_id must always be present
        assert record.get("assay_chembl_id") is not None

        # assay_type should always be present
        assert record.get("assay_type") is not None


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_assay_confidence_score(e2e_data_dir: Path):
    """E2E: Verify confidence_score is within valid range.

    ChEMBL confidence scores range from 0 to 9.
    """
    # Arrange
    ctx = create_test_context("chembl_assay", limit=5)

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Check confidence score range
    records = get_silver_records(e2e_data_dir, "chembl_assay")

    for record in records:
        confidence = record.get("confidence_score")
        if confidence is not None:
            assert 0 <= confidence <= 9, (
                f"Invalid confidence_score {confidence} for {record.get('assay_chembl_id')}"
            )
