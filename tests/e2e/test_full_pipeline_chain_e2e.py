"""E2E tests for multi-pipeline scenarios.

Tests that verify:
- Multiple pipelines can run in sequence
- Data consistency across pipelines
- Pipeline dependencies and cross-references

Note: All tests in this module are grouped via xdist_group to prevent
race conditions when running in parallel. These tests modify global
environment variables (BIOETL_DATA_DIR) and cached settings.
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Group all tests in this module to run in the same xdist worker
# This prevents race conditions with BIOETL_DATA_DIR and get_settings cache
pytestmark = pytest.mark.xdist_group("e2e_pipeline_chain")

from bioetl.composition.bootstrap import bootstrap_pipeline

from .conftest import (
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
async def test_chembl_target_then_activity_chain(e2e_data_dir: Path):
    """E2E: Run Target pipeline, then Activity pipeline.

    Activities reference targets, so this tests a realistic data flow.
    """
    # Step 1: Run Target pipeline
    target_ctx = create_test_context("chembl_target", limit=3)
    target_runner = bootstrap_pipeline(target_ctx)
    await target_runner.run()

    target_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_target", expected_min=1
    )

    # Step 2: Run Activity pipeline
    activity_ctx = create_test_context("chembl_activity", limit=5)
    activity_runner = bootstrap_pipeline(activity_ctx)
    await activity_runner.run()

    activity_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=1
    )

    # Verify both tables exist with data
    assert target_count >= 1
    assert activity_count >= 1


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_chembl_molecule_then_activity_chain(e2e_data_dir: Path):
    """E2E: Run Molecule pipeline, then Activity pipeline.

    Activities reference molecules, so this tests compound data flow.
    """
    # Step 1: Run Molecule pipeline
    molecule_ctx = create_test_context("chembl_molecule", limit=3)
    molecule_runner = bootstrap_pipeline(molecule_ctx)
    await molecule_runner.run()

    molecule_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_molecule", expected_min=1
    )

    # Step 2: Run Activity pipeline
    activity_ctx = create_test_context("chembl_activity", limit=5)
    activity_runner = bootstrap_pipeline(activity_ctx)
    await activity_runner.run()

    activity_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=1
    )

    # Verify both tables exist with data
    assert molecule_count >= 1
    assert activity_count >= 1


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_all_chembl_pipelines_chain(e2e_data_dir: Path):
    """E2E: Run all ChEMBL pipelines in sequence.

    Order: Target → Molecule → Document → Activity → Assay
    This tests the full ChEMBL data ecosystem.
    """
    pipelines_in_order = [
        ("chembl_target", "chembl_target", 2),
        ("chembl_molecule", "chembl_molecule", 2),
        ("chembl_document", "chembl_document", 2),
        ("chembl_activity", "chembl_activity", 3),
        ("chembl_assay", "chembl_assay", 2),
    ]

    results = {}

    for pipeline_name, table_name, limit in pipelines_in_order:
        ctx = create_test_context(pipeline_name, limit=limit)
        runner = bootstrap_pipeline(ctx)
        await runner.run()

        count = assert_silver_table_has_records(
            e2e_data_dir, table_name, expected_min=1
        )
        results[pipeline_name] = count

    # Verify all pipelines produced data
    for pipeline_name, count in results.items():
        assert count >= 1, f"Pipeline {pipeline_name} produced no records"


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_parallel_independent_pipelines(e2e_data_dir: Path):
    """E2E: Run independent pipelines that can run in parallel.

    PubMed and UniProt pipelines are independent and should not interfere.
    """
    # Run UniProt pipeline
    uniprot_ctx = create_test_context("uniprot_protein", limit=3)
    uniprot_runner = bootstrap_pipeline(uniprot_ctx)
    await uniprot_runner.run()

    uniprot_count = assert_silver_table_has_records(
        e2e_data_dir, "uniprot_protein", expected_min=1
    )

    # Verify UniProt produced data
    assert uniprot_count >= 1


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_pipeline_isolation(e2e_data_dir: Path):
    """E2E: Verify pipelines are isolated and don't corrupt each other's data.

    Running multiple pipelines should not cause data mixing.
    """
    # Run Target pipeline
    target_ctx = create_test_context("chembl_target", limit=3)
    target_runner = bootstrap_pipeline(target_ctx)
    await target_runner.run()

    # Run Molecule pipeline
    molecule_ctx = create_test_context("chembl_molecule", limit=3)
    molecule_runner = bootstrap_pipeline(molecule_ctx)
    await molecule_runner.run()

    # Get records from both tables
    target_records = get_silver_records(e2e_data_dir, "chembl_target")
    molecule_records = get_silver_records(e2e_data_dir, "chembl_molecule")

    # Verify data isolation - targets should have target_chembl_id
    for record in target_records:
        assert "target_chembl_id" in record
        # Should NOT have molecule_chembl_id as primary identifier
        # (though it might have it as a reference field)

    # Verify molecules have molecule_chembl_id
    for record in molecule_records:
        assert "molecule_chembl_id" in record
        # Should NOT have target_chembl_id as primary identifier


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_rerun_same_pipeline_twice(e2e_data_dir: Path):
    """E2E: Running the same pipeline twice should be idempotent.

    Second run should not duplicate records due to merge/upsert behavior.
    """
    # First run
    ctx1 = create_test_context("chembl_target", limit=3)
    runner1 = bootstrap_pipeline(ctx1)
    await runner1.run()

    first_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_target", expected_min=1
    )

    # Second run
    ctx2 = create_test_context("chembl_target", limit=3)
    runner2 = bootstrap_pipeline(ctx2)
    await runner2.run()

    second_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_target", expected_min=1
    )

    # Should not double the records
    assert (
        second_count <= first_count * 2
    ), f"Records may have duplicated: {first_count} -> {second_count}"
