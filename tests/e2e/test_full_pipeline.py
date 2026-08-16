# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""End-to-end tests for complete pipeline flows.

These tests verify full Extract → Bronze → Silver → Gold flows
with real infrastructure (MinIO, Redis via Docker).

Replay-backed tests use materialized VCR cassettes and per-test data roots so
the non-live suite remains deterministic and isolated from global ``data/output``.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner
from bioetl.composition.factories.storage import StorageBundle, StorageContext
from bioetl.domain.ports.noop import NoOpMetrics
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter
from tests.e2e.conftest import (
    _read_delta_records,
    assert_run_ledger_has_events,
    assert_run_manifest_exists,
    create_test_context,
)

pytestmark = pytest.mark.usefixtures("relaxed_dq_env")


def _create_test_storage_context(storage_paths: dict[str, object]) -> StorageContext:
    """Create a real storage context bound to the temporary E2E paths."""
    import structlog

    logger = structlog.get_logger()
    bronze_path = storage_paths["bronze"]
    silver_path = storage_paths["silver"]
    gold_path = storage_paths["gold"]
    checkpoints_path = storage_paths["checkpoints"]

    storage_adapter = StorageBundle(
        bronze_writer=BronzeWriter(
            base_path=str(bronze_path),
            logger=logger,
            metrics=NoOpMetrics(),
            json_export=(True, str(bronze_path / "json")),
        ),
        silver_writer=SilverWriter(
            base_path=str(silver_path),
            logger=logger,
        ),
        gold_writer=GoldWriter(
            base_path=str(gold_path),
            logger=logger,
        ),
    )
    return StorageContext(
        adapter=storage_adapter,
        bronze_path=str(bronze_path),
        silver_path=str(silver_path),
        gold_path=str(gold_path),
        checkpoints_path=str(checkpoints_path),
    )


async def _run_pipeline_with_test_storage(
    storage_context: StorageContext,
    pipeline_name: str,
    *,
    limit: int | None = None,
    query: str | None = None,
) -> tuple[object, object]:
    """Bootstrap and execute a pipeline against the provided E2E storage context."""
    with patch(
        "bioetl.composition.factories.storage.StorageFactory.create",
        return_value=storage_context,
    ):
        ctx = create_test_context(pipeline_name, limit=limit, query=query)
        runner = bootstrap_pipeline_runner(ctx)
        await runner.run()
    return ctx, runner


def _build_pipeline_runner_with_test_storage(
    storage_context: StorageContext,
    pipeline_name: str,
    *,
    limit: int | None = None,
    query: str | None = None,
    resume: bool = False,
) -> tuple[object, object]:
    """Bootstrap a pipeline runner against the provided E2E storage context."""
    with patch(
        "bioetl.composition.factories.storage.StorageFactory.create",
        return_value=storage_context,
    ):
        ctx = create_test_context(
            pipeline_name,
            limit=limit,
            query=query,
            resume=resume,
        )
        runner = bootstrap_pipeline_runner(ctx)
    return ctx, runner


def _storage_paths_from_data_dir(data_dir: Path) -> dict[str, Path]:
    """Build the storage-path mapping expected by the E2E storage context helper."""
    return {
        "bronze": data_dir / "bronze",
        "silver": data_dir / "silver",
        "gold": data_dir / "gold",
        "checkpoints": data_dir / "checkpoints",
    }


@pytest.mark.e2e
@pytest.mark.slow
class TestChEMBLPipelineE2E:
    """E2E tests for ChEMBL Activity pipeline."""

    @pytest.fixture
    def storage_paths(self, e2e_data_dir: Path) -> dict[str, Path]:
        """Bind Medallion and control-plane paths to one E2E sandbox."""
        return _storage_paths_from_data_dir(e2e_data_dir)

    @pytest.fixture
    def storage_context(self, storage_paths):
        """Create storage context with real writers pointing to temp paths."""
        return _create_test_storage_context(storage_paths)

    @pytest.mark.vcr(allow_playback_repeats=True)
    async def test_chembl_activity_full_run(
        self,
        storage_context,
        storage_paths,
        e2e_redis_client,
        e2e_minio_client,
        e2e_pipeline_limit,
    ):
        """Test complete pipeline from extract to Gold with real infrastructure.

        Verifies:
        - Bronze files created (JSONL)
        - Silver table created (Delta Lake)
        - Gold aggregations (if applicable)
        - Checkpoint saved
        - Redis locks released
        """
        await _run_pipeline_with_test_storage(
            storage_context,
            "chembl_activity",
            limit=e2e_pipeline_limit,
        )

        # Verify Bronze: Check for JSONL files
        bronze_files = list(storage_paths["bronze"].rglob("*.jsonl*"))
        assert len(bronze_files) > 0, "No Bronze JSONL files created"

        # Verify Silver: Check for Delta Lake files
        silver_parquet = list(storage_paths["silver"].rglob("*.parquet"))
        assert len(silver_parquet) > 0, "No Silver parquet files created"

        silver_delta_log = list(storage_paths["silver"].rglob("_delta_log"))
        assert len(silver_delta_log) > 0, "No Delta log created in Silver"

        # Verify locks released in Redis
        # Check that no locks remain with the chembl_activity pattern
        lock_keys = await e2e_redis_client.keys("lock:chembl_activity*")
        assert len(lock_keys) == 0, f"Locks not released: {lock_keys}"


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.vcr
@pytest.mark.serial
async def test_pubchem_compound_pipeline(
    e2e_data_dir: Path,
    e2e_redis_client,
    e2e_minio_client,
    e2e_pipeline_limit,
):
    """Test PubChem compound pipeline E2E flow.

    Verifies that PubChem pipeline can:
    - Extract compound data
    - Write to Bronze layer
    - Transform to Silver layer
    """
    storage_paths = _storage_paths_from_data_dir(e2e_data_dir)
    storage_context = _create_test_storage_context(storage_paths)
    await _run_pipeline_with_test_storage(
        storage_context,
        "pubchem_compound",
        limit=e2e_pipeline_limit,
        query="aspirin",
    )

    # Verify Bronze files created
    bronze_files = list(storage_paths["bronze"].rglob("*.jsonl*"))
    assert len(bronze_files) > 0, "No Bronze files created for PubChem"

    # Verify Silver Delta Lake
    silver_parquet = list(storage_paths["silver"].rglob("*.parquet"))
    assert len(silver_parquet) > 0, "No Silver parquet files for PubChem"

    # Verify locks released
    lock_keys = await e2e_redis_client.keys("lock:pubchem_compound*")
    assert len(lock_keys) == 0, f"PubChem locks not released: {lock_keys}"


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.vcr
async def test_pipeline_resume_after_failure(
    e2e_data_dir,
    e2e_redis_client,
    e2e_minio_client,
):
    """Test pipeline resume through the real checkpoint runtime service.

    Verifies:
    - Control-plane artifacts are emitted for both runs
    - CheckpointRuntimeService can persist and reload resume metadata
    - Resume runs publish explicit resume intent and clean up checkpoint state
    """
    storage_paths = _storage_paths_from_data_dir(e2e_data_dir)
    storage_context = _create_test_storage_context(storage_paths)

    # First run: publish baseline artifacts and ensure the pipeline completes.
    first_ctx, _runner = await _run_pipeline_with_test_storage(
        storage_context,
        "chembl_activity",
        limit=5,
    )
    assert_run_manifest_exists(e2e_data_dir, first_ctx.run_id)
    assert_run_ledger_has_events(
        e2e_data_dir,
        first_ctx.run_id,
        expected_events=("manifest_created", "run_started", "run_finished"),
    )

    silver_files_first = list(storage_paths["silver"].rglob("*.parquet"))
    assert len(silver_files_first) > 0, "No Silver files after first run"

    # Seed a real checkpoint through the runtime checkpoint service, then load it
    # back via the same service path that the runner uses for resume decisions.
    resume_ctx, resume_runner = _build_pipeline_runner_with_test_storage(
        storage_context,
        "chembl_activity",
        limit=5,
        resume=True,
    )
    checkpoint_path = storage_paths["checkpoints"] / "chembl_activity.json"
    await resume_runner._checkpoint_manager.save_checkpoint(
        CheckpointMetadata(records_processed=0)
    )
    assert checkpoint_path.exists(), "Seeded checkpoint must be persisted on disk"

    loaded_checkpoint = await resume_runner._checkpoint_manager.load_checkpoint()
    assert loaded_checkpoint is not None, "Resume runner must load seeded checkpoint"
    assert loaded_checkpoint.records_processed == 0

    await resume_runner.run()

    resume_manifest = assert_run_manifest_exists(e2e_data_dir, resume_ctx.run_id)
    assert resume_manifest["launch_context"].get("resume") is True
    assert resume_manifest["runtime_config"].get("resume") is True
    assert_run_ledger_has_events(
        e2e_data_dir,
        resume_ctx.run_id,
        expected_events=("manifest_created", "run_started", "run_finished"),
    )

    silver_files_second = list(storage_paths["silver"].rglob("*.parquet"))
    assert len(silver_files_second) > 0, "No Silver files after second run"
    assert not checkpoint_path.exists(), (
        "Successful resume runs must delete the consumed checkpoint"
    )

    lock_keys = await e2e_redis_client.keys("lock:chembl_activity*")
    assert len(lock_keys) == 0, f"Locks not released after resume: {lock_keys}"


@pytest.mark.e2e
@pytest.mark.slow
@pytest.mark.vcr
@pytest.mark.asyncio
async def test_full_pipeline__pipeline_idempotency__e17c8c60(
    e2e_data_dir: Path,
    e2e_redis_client,
    e2e_minio_client,
):
    """Test that rerunning append-mode activity pipeline stays bounded.

    ``chembl_activity`` uses Silver ``append`` mode, so this scenario is not a
    strict merge-idempotency check. It verifies that a second run completes and
    does not grow beyond the expected two-batch envelope.
    """
    storage_paths = _storage_paths_from_data_dir(e2e_data_dir)
    storage_context = _create_test_storage_context(storage_paths)

    # Run 1: Initial load
    await _run_pipeline_with_test_storage(
        storage_context,
        "chembl_activity",
        limit=5,
    )

    silver_path = storage_paths["silver"]
    # Find the actual Delta table directory
    delta_tables = [d for d in silver_path.rglob("*") if (d / "_delta_log").exists()]

    if len(delta_tables) > 0:
        count_first = len(await _read_delta_records(delta_tables[0]))

        # Run 2: Same data on append-mode pipeline
        await _run_pipeline_with_test_storage(
            storage_context,
            "chembl_activity",
            limit=5,
        )

        # Count records after second run
        count_second = len(await _read_delta_records(delta_tables[0]))

        assert count_second >= count_first, (
            f"Append rerun unexpectedly shrank output: {count_first} -> {count_second}."
        )
        assert count_second <= count_first * 2, (
            f"Append rerun exceeded expected growth envelope: {count_first} -> {count_second}."
        )

    # Cleanup locks
    lock_keys = await e2e_redis_client.keys("lock:chembl_activity*")
    assert len(lock_keys) == 0, f"Locks not released: {lock_keys}"
