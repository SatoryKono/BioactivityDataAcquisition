"""Unit tests for CompositePipelineRunner FSM integration.

Tests for FSM state management during seed pipeline execution phase.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.runner import (
    CompositePipelineRunner,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite.result import SeedResult
from bioetl.domain.composite.state import CompositePipelineState


@dataclass
class MockCompositeConfig:
    """Mock composite configuration for testing."""

    name: str = "test_composite"
    lock_key: str = "lock:test_composite"

    @dataclass
    class SeedConfig:
        pipeline: str = "chembl_activity"
        silver_table: str = "chembl_activity"
        output_keys: tuple[str, ...] = ("chembl_id",)

    @dataclass
    class MergeConfig:
        output_silver_path: str = "silver/composite"
        output_gold_path: str = "gold/composite"

    @dataclass
    class DQConfig:
        soft_fail_threshold: float = 0.05
        hard_fail_threshold: float = 0.20

    seed: SeedConfig = None  # type: ignore[assignment]
    merge: MergeConfig = None  # type: ignore[assignment]
    dq: DQConfig = None  # type: ignore[assignment]
    enrichers: tuple = ()
    required_enrichers: frozenset = frozenset()
    dependencies: tuple = ()

    def __post_init__(self):
        if self.seed is None:
            self.seed = self.SeedConfig()
        if self.merge is None:
            self.merge = self.MergeConfig()
        if self.dq is None:
            self.dq = self.DQConfig()


class MockPipelineRunner:
    """Mock PipelineRunner for testing."""

    def __init__(self, should_fail: bool = False, error_message: str = "Seed failed"):
        self._should_fail = should_fail
        self._error_message = error_message
        self.run_called = False
        self._executor = MagicMock()
        self._executor.records_fetched = 100
        self._executor.records_silver = 95

    async def run(self):
        self.run_called = True
        if self._should_fail:
            raise RuntimeError(self._error_message)


def create_mock_logger() -> MagicMock:
    """Create a mock logger."""
    logger = MagicMock()
    logger.info = MagicMock()
    logger.error = MagicMock()
    logger.warning = MagicMock()
    logger.debug = MagicMock()
    return logger


def create_mock_lock() -> AsyncMock:
    """Create a mock lock."""
    lock = AsyncMock()
    lock.acquire = AsyncMock(return_value=True)
    lock.release = AsyncMock(return_value=True)
    return lock


def create_mock_checkpoint_manager(
    initial_state: CompositeCheckpointState | None = None,
) -> AsyncMock:
    """Create a mock checkpoint manager."""
    manager = AsyncMock()
    if initial_state is None:
        initial_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            created_at=datetime.now(tz=UTC),
        )
    manager.load = AsyncMock(return_value=initial_state)
    manager.save = AsyncMock()
    manager.delete = AsyncMock()
    return manager


def create_mock_key_extractor() -> AsyncMock:
    """Create a mock key extractor."""
    import polars as pl

    extractor = AsyncMock()
    extractor.extract = AsyncMock(
        return_value=pl.DataFrame({"chembl_id": ["CHEMBL123"]})
    )
    return extractor


def create_mock_coordinator() -> AsyncMock:
    """Create a mock enrichment coordinator."""
    coordinator = AsyncMock()
    coordinator.run_enrichers = AsyncMock(return_value={})
    return coordinator


def create_mock_merger() -> AsyncMock:
    """Create a mock merger."""
    from bioetl.domain.composite.result import MergeResult

    merger = AsyncMock()
    merger.merge = AsyncMock(
        return_value=MergeResult(
            records_merged=100,
            records_from_seed=100,
            records_enriched=0,
            records_fully_enriched=0,
            duration_seconds=1.0,
        )
    )
    return merger


def create_runner(
    seed_runner: MockPipelineRunner | None = None,
    checkpoint_manager: AsyncMock | None = None,
    runtime: CompositeRuntimeConfig | None = None,
) -> CompositePipelineRunner:
    """Create a CompositePipelineRunner for testing."""
    if seed_runner is None:
        seed_runner = MockPipelineRunner()
    if checkpoint_manager is None:
        checkpoint_manager = create_mock_checkpoint_manager()
    if runtime is None:
        runtime = CompositeRuntimeConfig()

    return CompositePipelineRunner(
        config=MockCompositeConfig(),
        runtime=runtime,
        seed_runner_factory=lambda: seed_runner,
        enricher_runner_factory=lambda name, df: MockPipelineRunner(),
        key_extractor=create_mock_key_extractor(),
        coordinator=create_mock_coordinator(),
        merger=create_mock_merger(),
        checkpoint_manager=checkpoint_manager,
        logger=create_mock_logger(),
        lock=create_mock_lock(),
    )


class TestFSMSeedStateTransitions:
    """Tests for FSM state transitions during seed execution."""

    @pytest.mark.asyncio
    async def test_seed_running_state_set_before_seed_execution(self):
        """SEED_RUNNING state should be set before seed pipeline runs."""
        seed_runner = MockPipelineRunner()
        checkpoint_manager = create_mock_checkpoint_manager()
        runner = create_runner(
            seed_runner=seed_runner,
            checkpoint_manager=checkpoint_manager,
        )

        await runner.run()

        # Verify checkpoint was saved with SEED_RUNNING state
        save_calls = checkpoint_manager.save.call_args_list
        assert len(save_calls) >= 2, (
            "Should save checkpoint at least twice (SEED_RUNNING and SEED_COMPLETED)"
        )

        # First save should be SEED_RUNNING
        first_save_state = save_calls[0][0][0]
        assert first_save_state.state == CompositePipelineState.SEED_RUNNING

    @pytest.mark.asyncio
    async def test_seed_completed_state_set_after_successful_seed(self):
        """SEED_COMPLETED state should be set after successful seed execution."""
        seed_runner = MockPipelineRunner()
        checkpoint_manager = create_mock_checkpoint_manager()
        runner = create_runner(
            seed_runner=seed_runner,
            checkpoint_manager=checkpoint_manager,
        )

        await runner.run()

        # Verify checkpoint was saved with SEED_COMPLETED state
        save_calls = checkpoint_manager.save.call_args_list
        assert len(save_calls) >= 2

        # Second save should be SEED_COMPLETED
        second_save_state = save_calls[1][0][0]
        assert second_save_state.state == CompositePipelineState.SEED_COMPLETED
        assert second_save_state.seed_completed is True

    @pytest.mark.asyncio
    async def test_seed_completed_sets_seed_result(self):
        """SEED_COMPLETED state should include seed result."""
        seed_runner = MockPipelineRunner()
        checkpoint_manager = create_mock_checkpoint_manager()
        runner = create_runner(
            seed_runner=seed_runner,
            checkpoint_manager=checkpoint_manager,
        )

        await runner.run()

        save_calls = checkpoint_manager.save.call_args_list
        seed_completed_state = save_calls[1][0][0]
        assert seed_completed_state.seed_result is not None
        assert seed_completed_state.seed_result.pipeline_name == "chembl_activity"


class TestFSMSeedFailure:
    """Tests for FSM state transitions when seed fails."""

    @pytest.mark.asyncio
    async def test_failed_state_set_on_seed_error(self):
        """FAILED state should be set when seed pipeline fails."""
        seed_runner = MockPipelineRunner(
            should_fail=True, error_message="Connection timeout"
        )
        checkpoint_manager = create_mock_checkpoint_manager()
        runner = create_runner(
            seed_runner=seed_runner,
            checkpoint_manager=checkpoint_manager,
        )

        with pytest.raises(RuntimeError, match="Connection timeout"):
            await runner.run()

        # Verify checkpoint was saved with FAILED state
        save_calls = checkpoint_manager.save.call_args_list
        assert len(save_calls) >= 2, "Should save SEED_RUNNING then FAILED"

        # Last save should be FAILED
        last_save_state = save_calls[-1][0][0]
        assert last_save_state.state == CompositePipelineState.FAILED

    @pytest.mark.asyncio
    async def test_seed_completed_false_on_failure(self):
        """seed_completed should remain False when seed fails."""
        seed_runner = MockPipelineRunner(should_fail=True)
        checkpoint_manager = create_mock_checkpoint_manager()
        runner = create_runner(
            seed_runner=seed_runner,
            checkpoint_manager=checkpoint_manager,
        )

        with pytest.raises(RuntimeError):
            await runner.run()

        save_calls = checkpoint_manager.save.call_args_list
        last_save_state = save_calls[-1][0][0]
        assert last_save_state.seed_completed is False

    @pytest.mark.asyncio
    async def test_error_logged_on_seed_failure(self):
        """Error should be logged when seed fails."""
        seed_runner = MockPipelineRunner(should_fail=True, error_message="API error")
        checkpoint_manager = create_mock_checkpoint_manager()
        logger = create_mock_logger()

        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(),
            seed_runner_factory=lambda: seed_runner,
            enricher_runner_factory=lambda name, df: MockPipelineRunner(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=checkpoint_manager,
            logger=logger,
            lock=create_mock_lock(),
        )

        with pytest.raises(RuntimeError):
            await runner.run()

        # Verify error was logged
        error_calls = [
            c for c in logger.error.call_args_list if "Seed pipeline failed" in str(c)
        ]
        assert len(error_calls) >= 1, "Should log seed failure error"


class TestFSMSeedResume:
    """Tests for FSM state when resuming with completed seed."""

    @pytest.mark.asyncio
    async def test_seed_skipped_when_already_completed(self):
        """Seed pipeline should not run when already completed in checkpoint."""
        # Create initial state with seed completed
        initial_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            state=CompositePipelineState.SEED_COMPLETED,
            seed_completed=True,
            seed_result=SeedResult(
                pipeline_name="chembl_activity",
                records_extracted=100,
                records_silver=95,
                keys_generated=90,
                duration_seconds=10.0,
            ),
            created_at=datetime.now(tz=UTC),
        )
        checkpoint_manager = create_mock_checkpoint_manager(initial_state)
        seed_runner = MockPipelineRunner()

        runner = create_runner(
            seed_runner=seed_runner,
            checkpoint_manager=checkpoint_manager,
            runtime=CompositeRuntimeConfig(resume=True),
        )

        await runner.run()

        # Verify seed runner was NOT called
        assert seed_runner.run_called is False

    @pytest.mark.asyncio
    async def test_fsm_state_remains_seed_completed_on_resume(self):
        """FSM state should remain SEED_COMPLETED when resuming."""
        initial_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            state=CompositePipelineState.SEED_COMPLETED,
            seed_completed=True,
            seed_result=SeedResult(
                pipeline_name="chembl_activity",
                records_extracted=100,
                records_silver=95,
                keys_generated=90,
                duration_seconds=10.0,
            ),
            created_at=datetime.now(tz=UTC),
        )
        checkpoint_manager = create_mock_checkpoint_manager(initial_state)

        runner = create_runner(
            checkpoint_manager=checkpoint_manager,
            runtime=CompositeRuntimeConfig(resume=True),
        )

        result = await runner.run()

        # Verify result indicates resume
        assert result.seed_result is not None
        assert result.seed_result.resumed is True

    @pytest.mark.asyncio
    async def test_fsm_state_corrected_on_resume_with_inconsistent_state(self):
        """FSM state should be corrected to SEED_COMPLETED when resuming with old checkpoint."""
        # Create initial state with seed_completed=True but wrong FSM state (old checkpoint format)
        initial_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            state=CompositePipelineState.NOT_STARTED,  # Inconsistent with seed_completed=True
            seed_completed=True,
            seed_result=SeedResult(
                pipeline_name="chembl_activity",
                records_extracted=100,
                records_silver=95,
                keys_generated=90,
                duration_seconds=10.0,
            ),
            created_at=datetime.now(tz=UTC),
        )
        checkpoint_manager = create_mock_checkpoint_manager(initial_state)
        logger = create_mock_logger()

        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(resume=True),
            seed_runner_factory=lambda: MockPipelineRunner(),
            enricher_runner_factory=lambda name, df: MockPipelineRunner(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=checkpoint_manager,
            logger=logger,
            lock=create_mock_lock(),
        )

        await runner.run()

        # Verify FSM transition was logged
        transition_calls = [
            c for c in logger.info.call_args_list if "FSM state transition" in str(c)
        ]
        # Should log transition to SEED_COMPLETED
        assert any("seed_resume" in str(c) for c in transition_calls), (
            "Should log seed_resume transition"
        )


class TestFSMTransitionLogging:
    """Tests for FSM transition logging."""

    @pytest.mark.asyncio
    async def test_seed_start_transition_logged(self):
        """Transition to SEED_RUNNING should be logged."""
        logger = create_mock_logger()
        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(),
            seed_runner_factory=lambda: MockPipelineRunner(),
            enricher_runner_factory=lambda name, df: MockPipelineRunner(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=create_mock_checkpoint_manager(),
            logger=logger,
            lock=create_mock_lock(),
        )

        await runner.run()

        # Verify FSM transition to SEED_RUNNING was logged
        transition_calls = [
            c for c in logger.info.call_args_list if "FSM state transition" in str(c)
        ]
        assert any("seed_start" in str(c) for c in transition_calls)

    @pytest.mark.asyncio
    async def test_seed_complete_transition_logged(self):
        """Transition to SEED_COMPLETED should be logged."""
        logger = create_mock_logger()
        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(),
            seed_runner_factory=lambda: MockPipelineRunner(),
            enricher_runner_factory=lambda name, df: MockPipelineRunner(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=create_mock_checkpoint_manager(),
            logger=logger,
            lock=create_mock_lock(),
        )

        await runner.run()

        # Verify FSM transition to SEED_COMPLETED was logged
        transition_calls = [
            c for c in logger.info.call_args_list if "FSM state transition" in str(c)
        ]
        assert any("seed_complete" in str(c) for c in transition_calls)

    @pytest.mark.asyncio
    async def test_seed_failed_transition_logged(self):
        """Transition to FAILED should be logged when seed fails."""
        logger = create_mock_logger()
        seed_runner = MockPipelineRunner(should_fail=True)
        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(),
            seed_runner_factory=lambda: seed_runner,
            enricher_runner_factory=lambda name, df: MockPipelineRunner(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=create_mock_checkpoint_manager(),
            logger=logger,
            lock=create_mock_lock(),
        )

        with pytest.raises(RuntimeError):
            await runner.run()

        # Verify FSM transition to FAILED was logged
        transition_calls = [
            c for c in logger.info.call_args_list if "FSM state transition" in str(c)
        ]
        assert any("seed_failed" in str(c) for c in transition_calls)


class TestCheckpointSaveErrorHandling:
    """Tests for graceful checkpoint save error handling."""

    @pytest.mark.asyncio
    async def test_pipeline_continues_on_checkpoint_save_failure(self):
        """Pipeline should continue if checkpoint save fails."""
        checkpoint_manager = create_mock_checkpoint_manager()
        # First save (SEED_RUNNING) fails, but pipeline should continue
        checkpoint_manager.save = AsyncMock(
            side_effect=[Exception("Disk full"), None, None, None]
        )
        logger = create_mock_logger()

        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(),
            seed_runner_factory=lambda: MockPipelineRunner(),
            enricher_runner_factory=lambda name, df: MockPipelineRunner(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=checkpoint_manager,
            logger=logger,
            lock=create_mock_lock(),
        )

        # Should not raise despite checkpoint save failure
        result = await runner.run()
        assert result is not None

        # Warning should be logged
        warning_calls = [
            c
            for c in logger.warning.call_args_list
            if "checkpoint_save_failed" in str(c)
        ]
        assert len(warning_calls) >= 1

    @pytest.mark.asyncio
    async def test_warning_logged_on_checkpoint_save_failure(self):
        """Warning should be logged when checkpoint save fails."""
        checkpoint_manager = create_mock_checkpoint_manager()
        # First save fails (SEED_RUNNING), rest succeed for pipeline to complete
        checkpoint_manager.save = AsyncMock(
            side_effect=[OSError("Permission denied"), None, None, None, None, None]
        )
        logger = create_mock_logger()

        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(),
            seed_runner_factory=lambda: MockPipelineRunner(),
            enricher_runner_factory=lambda name, df: MockPipelineRunner(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=checkpoint_manager,
            logger=logger,
            lock=create_mock_lock(),
        )

        await runner.run()

        # Verify warning logged with correct context
        warning_calls = logger.warning.call_args_list
        assert any("checkpoint_save_failed" in str(c) for c in warning_calls)
        assert any("Permission denied" in str(c) for c in warning_calls)
