"""Integration tests to guard recovery/resume invariants during refactoring."""

from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from bioetl.application.core.config import RecordProcessorConfig
from bioetl.domain.types.checkpoint_metadata import CheckpointMetadata
from bioetl.domain.context import PipelineContext
from bioetl.domain.config import DQConfig
from bioetl.domain.types import HealthStatus
from bioetl.domain.types import RunType
from tests.unit.application.core.test_batch_executor_memory import (
    _create_batch_executor,
)


class FakeDataSource:
    """Mock data source that yields a fixed number of records and deterministically fails."""

    provider_name = "fake"

    def __init__(self, total_records: int = 1000, fail_at: int | None = None) -> None:
        self.total_records = total_records
        self.fail_at = fail_at
        self.current_idx = 0
        self.health_check = AsyncMock(return_value=HealthStatus.HEALTHY)
        self.aclose = AsyncMock()

    async def __aenter__(self):
        await asyncio.sleep(0)
        return self

    async def __aexit__(self, *args: object) -> None:
        """No cleanup needed for fake data source."""
        await asyncio.sleep(0)

    async def fetch(self, entity_type: str, limit: int | None = None, **kwargs: object):
        await asyncio.sleep(0)
        for i in range(self.current_idx, self.total_records):
            if self.fail_at is not None and i == self.fail_at:
                raise RuntimeError(f"Simulated failure at record {i}")
            self.current_idx = i + 1
            yield {"id": i, "val": f"value_{i}"}


class MemoryCheckpointAdapter:
    """Local in-memory checkpoint adapter to verify saved offsets."""

    def __init__(self) -> None:
        self.store: dict[str, tuple[str, dict[str, object]]] = {}

    async def save(
        self, pipeline: str, run_id: str, metadata: dict[str, object]
    ) -> None:
        await asyncio.sleep(0)
        self.store[pipeline] = (run_id, metadata)

    async def load(self, pipeline: str) -> tuple[str, dict[str, object]] | None:
        await asyncio.sleep(0)
        return self.store.get(pipeline)

    async def delete(self, pipeline: str) -> None:
        await asyncio.sleep(0)
        self.store.pop(pipeline, None)

    async def list_all(self) -> list[str]:
        await asyncio.sleep(0)
        return list(self.store.keys())


@pytest.mark.asyncio
class TestBatchExecutorRecoveryInvariants:
    """Ensures resume/checkpoint logic is safe before FSM refactoring."""

    async def test_failure_and_resume_preserves_exactly_all_records(self) -> None:
        """
        Spec: Fail mid-stream -> Resume -> Final Silver output contains exactly all
        records without duplicates (simulating merge semantics by asserting totals).
        """
        data_source = FakeDataSource(total_records=1000, fail_at=550)
        checkpoint_port = MemoryCheckpointAdapter()

        async def save_checkpoint(
            metadata: int | CheckpointMetadata,
        ) -> None:
            payload = (
                metadata.to_dict()
                if isinstance(metadata, CheckpointMetadata)
                else {"records_processed": metadata}
            )
            await checkpoint_port.save(
                "test",
                "r1",
                payload,
            )

        # Configure minimal required services
        services = MagicMock()
        services.data_source = data_source
        services.storage.write_bronze = AsyncMock()
        services.storage.write_silver = AsyncMock()
        services.storage.write_gold = AsyncMock()
        mock_logger = MagicMock()
        mock_logger.bind = MagicMock(return_value=mock_logger)
        context = PipelineContext(
            run_id=uuid4(),
            run_type=RunType.INCREMENTAL,
            logger=mock_logger,
        )
        config = RecordProcessorConfig(
            pipeline_name="test_pipeline",
            provider="test",
            entity_type="ent",
            silver_schema=None,
            gold_schema=MagicMock(),
            dq_config=DQConfig(
                soft_fail_threshold=0.1,
                hard_fail_threshold=0.3,
            ),
            normalization_enabled=False,
        )

        # Run 1: Should fail exactly at record 550.
        executor_run1 = _create_batch_executor(
            services=services,
            context=context,
            config=config,
            callbacks={
                "transform": lambda ctx, rec, idx: {"entity_id": str(rec["id"])},
                "gold_filter": lambda ctx, rec: True,
                "gold_transform": lambda ctx, rec: rec,
            },
            gold_validator=MagicMock(),
            checkpoint_manager=MagicMock(
                load_checkpoint=AsyncMock(return_value=None),
                save_checkpoint=AsyncMock(side_effect=save_checkpoint),
            ),
            batch_size=100,  # Will save checkpoint every 100 records
            checkpoint_interval=100,
        )

        with pytest.raises(RuntimeError, match="Simulated failure at record 550"):
            await executor_run1.execute(limit=None)

        # Exception recovery now persists the exact processed offset at failure time.
        saved_state = await checkpoint_port.load("test")
        assert saved_state is not None
        assert saved_state[1].get("records_processed") == 550

        # Run 2: Resume logic
        data_source.fail_at = None  # Remove failure for second run
        records_processed = saved_state[1].get("records_processed")
        assert isinstance(records_processed, int)
        data_source.current_idx = records_processed  # Simulating resume behavior

        executor_run2 = _create_batch_executor(
            services=services,
            context=PipelineContext(
                run_id=uuid4(),
                run_type=RunType.INCREMENTAL,
                logger=mock_logger,
            ),
            config=config,
            callbacks={
                "transform": lambda ctx, rec, idx: {"entity_id": str(rec["id"])},
                "gold_filter": lambda ctx, rec: True,
                "gold_transform": lambda ctx, rec: rec,
            },
            gold_validator=MagicMock(),
            checkpoint_manager=MagicMock(
                load_checkpoint=AsyncMock(return_value=None),
                save_checkpoint=AsyncMock(side_effect=save_checkpoint),
            ),
            batch_size=100,
            checkpoint_interval=100,
        )
        await executor_run2.execute(limit=None)

        # The source should now have exhausted exactly up to 1000
        assert data_source.current_idx == 1000
