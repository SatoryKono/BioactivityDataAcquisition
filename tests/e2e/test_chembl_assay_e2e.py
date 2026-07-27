"""E2E tests for ChEMBL Assay pipeline.

Tests the complete pipeline execution from fetch to Gold layer.
Uses VCR cassettes for HTTP requests and local file storage.

Cassettes location: tests/fixtures/vcr/chembl/
"""

from __future__ import annotations

from pathlib import Path

import pytest

from .conftest import (
    assert_bronze_files_exist,
    assert_run_manifest_exists,
    assert_silver_table_has_records,
    create_deterministic_test_context,
    create_test_context,
    get_silver_records,
    run_pipeline_or_skip_transient,
)
from tests.helpers.e2e_schema_assertions import (
    assert_optional_numeric_in_range,
    assert_records_have_required_fields,
)

pytestmark = pytest.mark.usefixtures("relaxed_dq_env")


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
    ctx = create_deterministic_test_context("chembl_assay", limit=5)

    # Act
    await run_pipeline_or_skip_transient(ctx)

    # Assert - Bronze layer
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "chembl", "assay")
    assert len(bronze_files) >= 1

    # Assert - Silver layer
    silver_count = await assert_silver_table_has_records(
        e2e_data_dir, "chembl_assay", expected_min=1
    )
    assert silver_count <= 5

    # Assert - Schema validation
    records = await get_silver_records(e2e_data_dir, "chembl_assay")
    required_fields = ["assay_id", "assay_type"]
    for record in records:
        for field in required_fields:
            assert field in record, f"Missing required field: {field}"

    manifest_payload = assert_run_manifest_exists(e2e_data_dir, ctx.run_id)
    assert manifest_payload["pipeline_name"] == "chembl_assay"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_assay_metadata_fields(e2e_data_dir: Path):
    """E2E: Verify assay metadata fields are extracted with schema-backed asserts."""
    ctx = create_test_context("chembl_assay", limit=5)
    await run_pipeline_or_skip_transient(ctx)
    records = await get_silver_records(e2e_data_dir, "chembl_assay")
    assert_records_have_required_fields(
        records,
        ("assay_id", "assay_type"),
        entity_label="chembl_assay.silver",
    )


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_assay_confidence_score(e2e_data_dir: Path):
    """E2E: Verify confidence_score is within valid range when present."""
    ctx = create_test_context("chembl_assay", limit=5)
    await run_pipeline_or_skip_transient(ctx)
    records = await get_silver_records(e2e_data_dir, "chembl_assay")
    assert_optional_numeric_in_range(
        records,
        "confidence_score",
        minimum=0,
        maximum=9,
        entity_label="chembl_assay.silver",
    )
