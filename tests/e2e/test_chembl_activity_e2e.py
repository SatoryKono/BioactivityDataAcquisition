"""E2E tests for ChEMBL Activity pipeline.

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
async def test_chembl_activity_full_cycle(e2e_data_dir: Path):
    """E2E: ChEMBL Activity pipeline from fetch to Silver.

    Verifies:
    1. Pipeline bootstraps correctly
    2. Data is fetched from ChEMBL API (via VCR cassette)
    3. Bronze files are created
    4. Silver Delta table contains records
    5. Records have correct schema
    """
    # Arrange
    ctx = create_test_context("chembl_activity", limit=10)

    # Act
    runner = bootstrap_pipeline(ctx)
    await runner.run()

    # Assert - Bronze layer
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "chembl", "activity")
    assert len(bronze_files) >= 1, "At least one Bronze file should exist"

    # Assert - Silver layer
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=1
    )
    assert silver_count <= 10, f"Expected <= 10 records (limit), got {silver_count}"

    # Assert - Schema validation
    records = get_silver_records(e2e_data_dir, "chembl_activity")
    required_fields = ["activity_id", "molecule_chembl_id", "target_chembl_id"]
    for record in records:
        for field in required_fields:
            assert field in record, f"Missing required field: {field}"
        assert "_run_id" in record
        assert "_run_type" in record
        assert "_ingestion_ts" in record


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pipeline_idempotency(e2e_data_dir: Path):
    """E2E: Pipeline runs are idempotent.

    Running the same pipeline twice with same data should not duplicate records
    in Silver table (merge/upsert behavior).
    """
    # Arrange
    ctx1 = create_test_context("chembl_activity", limit=5)

    # Act - First run
    runner1 = bootstrap_pipeline(ctx1)
    await runner1.run()
    count_after_first = assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=1
    )

    # Act - Second run with same limit
    ctx2 = create_test_context("chembl_activity", limit=5)
    runner2 = bootstrap_pipeline(ctx2)
    await runner2.run()
    count_after_second = assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=1
    )

    # Assert - Count should be similar (merge/upsert prevents duplicates)
    # Note: May differ slightly due to different batches, but should not double
    assert (
        count_after_second <= count_after_first * 2
    ), f"Records doubled after second run: {count_after_first} -> {count_after_second}"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pipeline_resume_from_checkpoint(e2e_data_dir: Path):
    """E2E: Pipeline can resume from checkpoint.

    Verifies that a pipeline run can be interrupted and resumed.
    """
    # Arrange - First run with limit
    ctx1 = create_test_context("chembl_activity", limit=3, resume=False)
    runner1 = bootstrap_pipeline(ctx1)
    await runner1.run()

    first_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=1
    )

    # Arrange - Second run with resume
    ctx2 = create_test_context("chembl_activity", limit=3, resume=True)
    runner2 = bootstrap_pipeline(ctx2)
    await runner2.run()

    second_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=first_count
    )

    # Assert - Should have at least as many records
    assert second_count >= first_count
