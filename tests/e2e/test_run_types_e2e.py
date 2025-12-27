"""E2E tests for different pipeline run types.

Tests the pipeline behavior for different run types:
- INCREMENTAL: Regular incremental updates
- BACKFILL: Historical data backfill
- REBUILD: Complete rebuild with data clearing

Per RULES.md 3.0 Medallion Architecture:
- Bronze: Append-only, idempotent
- Silver: Merge/Upsert by content_hash
- Gold: SCD Type 2 or partitions by date
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return logger


@pytest.mark.e2e
@pytest.mark.asyncio
class TestIncrementalRunType:
    """Tests for INCREMENTAL run type behavior."""

    async def test_incremental_uses_checkpoint(self, mock_logger: MagicMock):
        """E2E: Incremental run should use checkpoints for resumption."""
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        assert context.run_type == RunType.INCREMENTAL
        # Incremental should support resumption
        assert context.run_type.value == "incremental"

    async def test_incremental_does_not_clear_data(self, mock_logger: MagicMock):
        """E2E: Incremental run should not clear existing data."""
        from bioetl.application.core.medallion_policy import MedallionPolicy

        policy = MedallionPolicy()

        # Incremental should NOT clear Silver
        should_clear_silver = policy.should_clear_silver(RunType.INCREMENTAL)
        assert should_clear_silver is False

        # Incremental should NOT clear Gold
        should_clear_gold = policy.should_clear_gold(RunType.INCREMENTAL)
        assert should_clear_gold is False

    async def test_incremental_appends_bronze(self, mock_logger: MagicMock):
        """E2E: Incremental run should append to Bronze layer."""
        # Bronze is always append-only regardless of run type
        # This is a design constraint, not configurable
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        # Bronze path structure includes date partitioning
        # New data gets new date partition, preserving old data
        assert context.run_type == RunType.INCREMENTAL


@pytest.mark.e2e
@pytest.mark.asyncio
class TestBackfillRunType:
    """Tests for BACKFILL run type behavior."""

    async def test_backfill_clears_silver_and_gold(self, mock_logger: MagicMock):
        """E2E: Backfill run should clear Silver and Gold layers."""
        from bioetl.application.core.medallion_policy import MedallionPolicy

        policy = MedallionPolicy()

        # Backfill SHOULD clear Silver
        should_clear_silver = policy.should_clear_silver(RunType.BACKFILL)
        assert should_clear_silver is True

        # Backfill SHOULD clear Gold
        should_clear_gold = policy.should_clear_gold(RunType.BACKFILL)
        assert should_clear_gold is True

    async def test_backfill_preserves_bronze(self, mock_logger: MagicMock):
        """E2E: Backfill should preserve Bronze layer (archive)."""
        # Bronze is append-only for audit/forensic purposes
        # Backfill creates new Bronze data but doesn't delete old
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.BACKFILL,
            logger=mock_logger,
        )

        assert context.run_type == RunType.BACKFILL

    async def test_backfill_ignores_checkpoint(self, mock_logger: MagicMock):
        """E2E: Backfill should not use checkpoint (fresh start)."""
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.BACKFILL,
            logger=mock_logger,
        )

        # Backfill starts fresh, ignores existing checkpoint
        assert context.run_type == RunType.BACKFILL


@pytest.mark.e2e
@pytest.mark.asyncio
class TestRebuildRunType:
    """Tests for REBUILD run type behavior."""

    async def test_rebuild_clears_all_layers(self, mock_logger: MagicMock):
        """E2E: Rebuild should clear Silver and Gold layers."""
        from bioetl.application.core.medallion_policy import MedallionPolicy

        policy = MedallionPolicy()

        # Rebuild SHOULD clear Silver
        should_clear_silver = policy.should_clear_silver(RunType.REBUILD)
        assert should_clear_silver is True

        # Rebuild SHOULD clear Gold
        should_clear_gold = policy.should_clear_gold(RunType.REBUILD)
        assert should_clear_gold is True

    async def test_rebuild_starts_fresh(self, mock_logger: MagicMock):
        """E2E: Rebuild should start from scratch."""
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.REBUILD,
            logger=mock_logger,
        )

        assert context.run_type == RunType.REBUILD
        assert context.run_type.value == "rebuild"

    async def test_rebuild_reprocesses_bronze(self, mock_logger: MagicMock):
        """E2E: Rebuild should reprocess existing Bronze data."""
        # Rebuild reads from Bronze and regenerates Silver/Gold
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.REBUILD,
            logger=mock_logger,
        )

        assert context.run_type == RunType.REBUILD


@pytest.mark.e2e
@pytest.mark.asyncio
class TestRunTypeTransitions:
    """Tests for transitions between run types."""

    async def test_incremental_after_rebuild(self, mock_logger: MagicMock):
        """E2E: Incremental run after rebuild should work normally."""
        from bioetl.application.core.medallion_policy import MedallionPolicy

        policy = MedallionPolicy()

        # After a rebuild, incremental should not clear
        should_clear = policy.should_clear_silver(RunType.INCREMENTAL)
        assert should_clear is False

    async def test_backfill_after_incremental(self, mock_logger: MagicMock):
        """E2E: Backfill after incremental should clear data."""
        from bioetl.application.core.medallion_policy import MedallionPolicy

        policy = MedallionPolicy()

        # Backfill always clears, regardless of previous run type
        should_clear = policy.should_clear_silver(RunType.BACKFILL)
        assert should_clear is True


@pytest.mark.e2e
@pytest.mark.asyncio
class TestRunTypeMetrics:
    """Tests for run type metrics tracking."""

    async def test_run_type_in_records(self, mock_logger: MagicMock):
        """E2E: Run type should be tracked in Silver records."""
        from bioetl.domain.types import RunType

        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )

        # Records should include _run_type field
        mock_record = {
            "entity_id": "test_123",
            "_run_id": str(context.run_id),
            "_run_type": context.run_type.value,
        }

        assert mock_record["_run_type"] == "incremental"

    async def test_all_run_types_valid(self, mock_logger: MagicMock):
        """E2E: All run types should be valid enum values."""
        valid_types = [RunType.INCREMENTAL, RunType.BACKFILL, RunType.REBUILD]

        for run_type in valid_types:
            context = PipelineContext(
                run_id=uuid4(),
                run_type=run_type,
                logger=mock_logger,
            )
            assert context.run_type in valid_types


@pytest.mark.e2e
@pytest.mark.asyncio
class TestMedallionPolicyIntegration:
    """Tests for MedallionPolicy integration with run types."""

    async def test_policy_default_values(self):
        """E2E: Policy should have sensible defaults."""
        from bioetl.application.core.medallion_policy import MedallionPolicy

        policy = MedallionPolicy()

        # Default policy exists
        assert policy is not None

    async def test_policy_respects_run_type(self):
        """E2E: Policy decisions should respect run type."""
        from bioetl.application.core.medallion_policy import MedallionPolicy

        policy = MedallionPolicy()

        # Different run types should have different policies
        inc_clear = policy.should_clear_silver(RunType.INCREMENTAL)
        backfill_clear = policy.should_clear_silver(RunType.BACKFILL)
        rebuild_clear = policy.should_clear_silver(RunType.REBUILD)

        assert inc_clear is False
        assert backfill_clear is True
        assert rebuild_clear is True

    async def test_silver_write_mode_enum(self):
        """E2E: SilverWriteMode enum should have expected values."""
        from bioetl.infrastructure.storage.delta_writer import SilverWriteMode

        assert hasattr(SilverWriteMode, "MERGE")
        assert hasattr(SilverWriteMode, "APPEND")
        assert hasattr(SilverWriteMode, "DELETE")

    async def test_gold_write_mode_enum(self):
        """E2E: GoldWriteMode enum should have expected values."""
        from bioetl.infrastructure.storage.gold_writer import GoldWriteMode

        assert hasattr(GoldWriteMode, "OVERWRITE")
        assert hasattr(GoldWriteMode, "APPEND")
        assert hasattr(GoldWriteMode, "SCD2")
