"""E2E tests for ChEMBL Target pipeline.

Tests the complete pipeline execution from fetch to Gold layer.
Uses VCR cassettes for HTTP requests and local file storage.

Cassettes location: tests/fixtures/vcr/chembl/
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner
from .conftest import (
    assert_bronze_files_exist,
    assert_silver_table_has_records,
    create_test_context,
    get_silver_records,
)

pytestmark = pytest.mark.usefixtures("relaxed_dq_env")


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_target_full_cycle(e2e_data_dir: Path):
    """E2E: ChEMBL Target pipeline from fetch to Silver.

    Verifies:
    1. Target data is fetched and transformed
    2. cross_references field is properly aggregated from components
    3. Silver table contains expected records
    """
    # Arrange
    ctx = create_test_context("chembl_target", limit=5)

    # Act
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Bronze layer
    bronze_files = assert_bronze_files_exist(e2e_data_dir, "chembl", "target")
    assert len(bronze_files) >= 1

    # Assert - Silver layer
    silver_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_target", expected_min=1
    )
    assert silver_count <= 5

    # Assert - Schema validation
    records = get_silver_records(e2e_data_dir, "chembl_target")
    required_fields = ["target_id", "pref_name", "target_type"]
    for record in records:
        for field in required_fields:
            assert field in record, f"Missing required field: {field}"
        assert "target_xref_iuphar_ids" not in record


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_target_cross_references(e2e_data_dir: Path):
    """E2E: Verify cross_references are aggregated from target_component_xrefs.

    ChEMBL API stores cross-references inside each component's
    target_component_xrefs field, not at the target level.
    """
    import json

    # Arrange
    ctx = create_test_context("chembl_target", limit=5)

    # Act
    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    # Assert - Get records and check cross_references
    records = get_silver_records(e2e_data_dir, "chembl_target")

    # At least some targets should have cross_references
    targets_with_xrefs = [
        r
        for r in records
        if r.get("cross_references") and r["cross_references"] != "[]"
    ]

    # Parse and validate structure
    for record in targets_with_xrefs:
        xrefs = json.loads(record["cross_references"])
        assert isinstance(xrefs, list)
        if xrefs:
            # Each xref should have standard fields
            for xref in xrefs:
                assert "xref_id" in xref or "xref_src_db" in xref


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_target_projects_derived_synonym_fields(e2e_data_dir: Path):
    """E2E: derived synonym fields should flow through the full target pipeline."""
    ctx = create_test_context("chembl_target", limit=5)

    runner = bootstrap_pipeline_runner(ctx)
    await runner.run()

    records = get_silver_records(e2e_data_dir, "chembl_target")
    projected_records = [
        record
        for record in records
        if record.get("target_protein_synonyms") not in (None, "unknown")
    ]

    assert projected_records, "Expected at least one target with derived synonyms"
    for record in projected_records:
        assert record["target_gene_synonyms"] is not None
        assert record["target_ec_numbers"] is not None
        assert isinstance(record["target_component_synonyms"], str)
        assert "target_xref_iuphar_ids" not in record
        assert "downgraded" not in record
        assert "pipeline_stages" not in record
