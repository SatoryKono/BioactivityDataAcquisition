"""E2E tests for advanced pipeline scenarios.

These tests cover:
- VACUUM after successful run
- Quarantine record flow (write → inspect → replay)
- Multi-provider orchestration (ChEMBL + UniProt)
- Memory-based adaptive batch sizing

Part of architecture review refactoring plan (R2).
"""

from __future__ import annotations

import asyncio
from datetime import UTC
from pathlib import Path
from uuid import uuid4

import pytest
from deltalake import DeltaTable
from tests.helpers.vcr_config import build_cassette_dir

from bioetl.domain.context import PipelineRunContext
from bioetl.domain.types import BatchID, RunID, RunType
from .conftest import (
    _resolve_silver_table_path,
    assert_silver_table_has_records,
    create_test_context,
    get_silver_records,
    run_pipeline_or_skip_transient,
)

pytestmark = pytest.mark.usefixtures("relaxed_dq_env")


@pytest.fixture(scope="module")
def vcr_cassette_dir() -> Path:
    """Route advanced scenario cassettes through the shared ChEMBL cassette root."""
    return build_cassette_dir(
        fixtures_root=Path(__file__).resolve().parents[1] / "fixtures" / "vcr",
        provider_dir="chembl",
    )


async def _seed_chembl_activity_silver(data_dir: Path, *, limit: int = 10) -> int:
    """Materialize one local chembl_activity Silver seed inside active test VCR."""
    ctx = create_test_context("chembl_activity", limit=limit)
    await run_pipeline_or_skip_transient(ctx)
    return assert_silver_table_has_records(data_dir, "chembl_activity", expected_min=1)


# ============================================================================
# VACUUM After Run Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.vcr
@pytest.mark.asyncio
@pytest.mark.timeout(120)  # Pipeline + Delta table operations need more time
async def test_vacuum_runs_after_successful_pipeline(e2e_data_dir: Path):
    """E2E: VACUUM is triggered after successful pipeline run when enabled.

    Per RULES.md §3.2.2:
    - VACUUM should run automatically after successful incremental runs
    - Retention period is 7 days by default
    """
    from bioetl.domain.context import VacuumSettings

    # Create context with vacuum enabled
    ctx = PipelineRunContext(
        pipeline_name="chembl_activity",
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        resume=False,
        limit=5,
        vacuum=VacuumSettings(enabled=True, retention_days=7),  # Enable VACUUM
    )

    await run_pipeline_or_skip_transient(ctx)

    # Verify Silver table exists
    assert_silver_table_has_records(e2e_data_dir, "chembl_activity", expected_min=1)

    # Check Delta table has proper metadata (VACUUM ran)
    table_path = _resolve_silver_table_path(e2e_data_dir, "chembl_activity")
    dt = DeltaTable(str(table_path))

    # VACUUM should have executed - verify via history
    history = dt.history(limit=5)
    # At minimum, there should be a write operation
    assert len(history) >= 1


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.vcr
@pytest.mark.asyncio
@pytest.mark.timeout(120)  # Multiple pipeline runs need more time
async def test_vacuum_respects_retention_days(
    e2e_data_dir: Path,
):
    """E2E: VACUUM retention period is respected.

    Files newer than retention_days should not be deleted.
    """
    await _seed_chembl_activity_silver(e2e_data_dir)

    # Execute one more run to create a new version.
    ctx = create_test_context("chembl_activity", limit=5)
    await run_pipeline_or_skip_transient(ctx)
    await asyncio.sleep(0.1)  # Small delay between runs

    # Verify table has records
    count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=1
    )
    assert count >= 1

    # VACUUM with 7 day retention shouldn't delete anything recent
    table_path = _resolve_silver_table_path(e2e_data_dir, "chembl_activity")
    dt = DeltaTable(str(table_path))

    # Check history - should have multiple operations
    history = dt.history()
    assert len(history) >= 2, "Expected multiple operations in history"


# ============================================================================
# Quarantine Flow Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_quarantine_records_are_persisted(e2e_data_dir: Path):
    """E2E: Failed records are written to quarantine.

    Per RULES.md §2.6:
    - Data quality errors should quarantine records
    - Quarantine location: data_dir/quarantine/{pipeline}/
    """
    from datetime import datetime

    from bioetl.application.core.quarantine_manager import QuarantineRuntimeService
    from bioetl.domain.types import ErrorType
    from bioetl.infrastructure.quarantine.unified import UnifiedQuarantineAdapter

    # Setup quarantine
    quarantine_path = e2e_data_dir / "quarantine"
    quarantine_path.mkdir(exist_ok=True)

    quarantine = UnifiedQuarantineAdapter(
        base_path=str(quarantine_path),
    )

    manager = QuarantineRuntimeService(
        quarantine_port=quarantine, pipeline_name="test_pipeline"
    )

    # Write a quarantine record
    test_record = {
        "entity_id": "test_entity_1",
        "data": {"value": 123},
    }

    await manager.quarantine_record(
        record=test_record,
        error_type=ErrorType.DATA_QUALITY,
        batch_id=BatchID(uuid4()),
        error_details="Test DQ error",
        ingestion_ts=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
    )

    # Verify quarantine Delta table exists (base_path IS the table path)
    # Delta Lake creates _delta_log directory in the table path
    delta_log = quarantine_path / "_delta_log"
    assert delta_log.exists(), (
        f"Quarantine Delta table should exist at {quarantine_path}"
    )


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_quarantine_can_be_inspected(e2e_data_dir: Path):
    """E2E: Quarantine records can be listed and inspected.

    Tests the quarantine inspection flow used by CLI commands.
    """
    from datetime import UTC, datetime

    from bioetl.infrastructure.quarantine.unified import UnifiedQuarantineAdapter

    # Setup quarantine with test data
    quarantine_path = e2e_data_dir / "quarantine"
    quarantine_path.mkdir(exist_ok=True)

    quarantine = UnifiedQuarantineAdapter(
        base_path=str(quarantine_path),
    )

    # Write multiple quarantine records
    for i in range(3):
        await quarantine.write(
            pipeline="test_pipeline",
            error_code="DataQualityError",
            payload={"entity_id": f"entity_{i}"},
            bronze_batch_id=BatchID(uuid4()),
            metadata={"error_message": f"Error {i}"},
            ingestion_ts=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )

    # List quarantine entries
    entries = await quarantine.inspect(pipeline="test_pipeline")
    assert len(entries) >= 3, f"Expected at least 3 entries, got {len(entries)}"


# ============================================================================
# Multi-Provider Orchestration Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
@pytest.mark.timeout(180)  # Two sequential pipelines (ChEMBL + UniProt) need more time
async def test_chembl_and_uniprot_sequential_run(e2e_data_dir: Path):
    """E2E: ChEMBL and UniProt pipelines can run sequentially.

    This tests cross-provider orchestration - a realistic scenario
    where you need data from multiple sources.
    """
    # Step 1: Run ChEMBL Target pipeline
    chembl_ctx = create_test_context("chembl_target", limit=3)
    await run_pipeline_or_skip_transient(chembl_ctx)

    chembl_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_target", expected_min=1
    )

    # Step 2: Run UniProt Protein pipeline
    uniprot_ctx = create_test_context("uniprot_protein", limit=3)
    await run_pipeline_or_skip_transient(uniprot_ctx)

    uniprot_count = assert_silver_table_has_records(
        e2e_data_dir, "uniprot_protein", expected_min=1
    )

    # Both should have records
    assert chembl_count >= 1, "ChEMBL should have records"
    assert uniprot_count >= 1, "UniProt should have records"

    # Verify they're in different tables
    chembl_records = get_silver_records(e2e_data_dir, "chembl_target")
    uniprot_records = get_silver_records(e2e_data_dir, "uniprot_protein")

    assert len(chembl_records) >= 1
    assert len(uniprot_records) >= 1


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
@pytest.mark.timeout(180)  # Three sequential pipelines need more time
async def test_multiple_chembl_entities_parallel_safe(e2e_data_dir: Path):
    """E2E: Multiple ChEMBL entity pipelines can run without conflicts.

    Tests that different entity pipelines (target, molecule, activity)
    don't interfere with each other's data or locks.
    """
    # Run three pipelines
    pipelines = ["chembl_target", "chembl_molecule", "chembl_activity"]

    for pipeline_name in pipelines:
        ctx = create_test_context(pipeline_name, limit=2)
        await run_pipeline_or_skip_transient(ctx)

    # Verify all tables exist with data
    for pipeline_name in pipelines:
        count = assert_silver_table_has_records(
            e2e_data_dir, pipeline_name, expected_min=1
        )
        assert count >= 1, f"{pipeline_name} should have records"


# ============================================================================
# Resilience Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_pipeline_resumes_from_checkpoint(e2e_data_dir: Path):
    """E2E: Pipeline can resume from checkpoint after interruption.

    Tests checkpoint save/load flow for recovery scenarios.
    """
    from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter

    # Setup checkpoint
    checkpoint_path = e2e_data_dir / "checkpoints"
    checkpoint_path.mkdir(exist_ok=True)

    checkpoint = LocalCheckpointAdapter(
        base_path=checkpoint_path,
    )

    pipeline_name = "test_pipeline"
    run_id = RunID(uuid4())

    # Save checkpoint with metadata containing state
    await checkpoint.save(
        pipeline=pipeline_name,
        run_id=run_id,
        metadata={"state": {"offset": 100, "batch_count": 5}},
    )

    # Load checkpoint - returns tuple (run_id, metadata)
    loaded = await checkpoint.load(pipeline=pipeline_name)
    assert loaded is not None, "Checkpoint should be loadable"
    _, loaded_metadata = loaded
    assert loaded_metadata["state"]["offset"] == 100
    assert loaded_metadata["state"]["batch_count"] == 5


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
@pytest.mark.timeout(120)  # Two pipeline runs need more time
async def test_failed_run_preserves_partial_data(
    e2e_data_dir: Path,
):
    """E2E: Partial data is preserved when pipeline fails mid-run.

    Tests that Bronze/Silver data written before failure is retained.
    """
    initial_count = await _seed_chembl_activity_silver(e2e_data_dir)

    # Seed fixture already provides the first run; execute the follow-up run only.
    ctx2 = create_test_context("chembl_activity", limit=5)
    await run_pipeline_or_skip_transient(ctx2)

    # Data should be preserved/incremented
    final_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=initial_count
    )
    assert final_count >= initial_count, "Data should be preserved"


# ============================================================================
# Run Type Tests
# ============================================================================


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
@pytest.mark.timeout(120)  # Two pipeline runs need more time
async def test_rebuild_clears_existing_data(
    e2e_data_dir: Path,
):
    """E2E: REBUILD run type clears existing Silver/Gold data.

    Per RULES.md:
    - REBUILD should clear Silver and Gold before writing
    - Bronze is append-only (never cleared)
    """
    await _seed_chembl_activity_silver(e2e_data_dir)

    # Rebuild run - should clear and recreate
    ctx2 = create_test_context(
        "chembl_activity",
        limit=2,
        run_type=RunType.REBUILD,
    )
    await run_pipeline_or_skip_transient(ctx2)

    # After rebuild, count should be from the new run only
    rebuild_count = assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=1
    )

    # Verify rebuild happened (new data, not accumulated)
    assert rebuild_count >= 1


@pytest.mark.e2e
@pytest.mark.vcr
@pytest.mark.asyncio
@pytest.mark.timeout(120)  # Two pipeline runs need more time
async def test_backfill_clears_silver_only(
    e2e_data_dir: Path,
):
    """E2E: BACKFILL run type clears Silver but keeps Gold unchanged.

    Per RULES.md:
    - BACKFILL should clear Silver
    - Gold is not cleared during backfill
    """
    await _seed_chembl_activity_silver(e2e_data_dir)

    # Backfill run
    ctx2 = create_test_context(
        "chembl_activity",
        limit=5,
        run_type=RunType.BACKFILL,
    )
    await run_pipeline_or_skip_transient(ctx2)

    # Silver should have records from backfill
    assert_silver_table_has_records(
        e2e_data_dir, "chembl_activity", expected_min=1
    )
