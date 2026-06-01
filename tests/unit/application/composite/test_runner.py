"""Unit tests for CompositePipelineRunner FSM integration.

Tests for FSM state management during seed pipeline execution phase.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from unittest.mock import patch
from uuid import uuid4

import pytest

from bioetl.application.composite.checkpoint import CompositeCheckpointState
from bioetl.application.composite.runner_pkg import (
    CompositePipelineRunner,
    CompositeRunnerDependencies,
    CompositeRuntimeConfig,
)
from bioetl.application.composite.runtime_models import CompositeExecutionContext
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
    MergeResult,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.control_plane.run_ledger import COMPOSITE_RUN_LEDGER_STAGE_NAMES
from bioetl.domain.exceptions import StorageError
from bioetl.domain.exceptions.pipeline_shutdown import PipelineShutdownError
from tests.unit.application.composite.runner_test_support import (
    MockCompositeConfig,
    MockPipelineRunner,
    create_mock_checkpoint_manager,
    create_mock_coordinator,
    create_mock_fsm_state_helper,
    create_mock_key_extractor,
    create_mock_lock,
    create_mock_logger,
    create_mock_merger,
    new_enricher_runner_factory,
    new_seed_runner_factory,
    seed_runner_factory,
)


pytestmark = pytest.mark.unit

def create_runner(
    seed_runner: MockPipelineRunner | None = None,
    checkpoint_manager: AsyncMock | None = None,
    runtime: CompositeRuntimeConfig | None = None,
    manifest_id: str | None = None,
    run_ledger_service: MagicMock | None = None,
    metrics: MagicMock | None = None,
) -> CompositePipelineRunner:
    """Create a CompositePipelineRunner for testing."""
    if seed_runner is None:
        seed_runner = MockPipelineRunner()
    if checkpoint_manager is None:
        checkpoint_manager = create_mock_checkpoint_manager()
    if runtime is None:
        runtime = CompositeRuntimeConfig()
    config = MockCompositeConfig()
    logger = create_mock_logger()
    run_id = str(uuid4())

    deps = CompositeRunnerDependencies(
        seed_runner_factory=seed_runner_factory(seed_runner),
        enricher_runner_factory=new_enricher_runner_factory(),
        key_extractor=create_mock_key_extractor(),
        coordinator=create_mock_coordinator(),
        merger=create_mock_merger(),
        checkpoint_manager=checkpoint_manager,
        logger=logger,
        lock=create_mock_lock(),
        fsm_state_helper=create_mock_fsm_state_helper(
            logger=logger,
            config=config,
            run_id=run_id,
        ),
        manifest_id=manifest_id,
        metrics=metrics,
        run_ledger_service=run_ledger_service,
    )
    return CompositePipelineRunner(
        config=config,
        runtime=runtime,
        deps=deps,
        run_id=run_id,
    )


def _composite_execution_context() -> CompositeExecutionContext:
    """Build a stable composite execution context for focused runner tests."""
    return CompositeExecutionContext(
        seed_result=SeedResult(
            pipeline_name="chembl_activity",
            records_extracted=100,
            records_silver=95,
            keys_generated=95,
        ),
        dependency_results={},
        enrichment_results={},
        merge_result=MergeResult(
            records_merged=100,
            records_from_seed=100,
            records_enriched=0,
            records_fully_enriched=0,
            duration_seconds=1.0,
        ),
    )


class TestFSMSeedStateTransitions:
    """Tests for FSM state transitions during seed execution."""

    @pytest.mark.unit
    def test_start_run_lifecycle_uses_captured_runtime_timing_anchor(self) -> None:
        runner = create_runner()
        started_at = datetime(2026, 4, 13, 10, 0, tzinfo=UTC)
        runner._observer.emit_run_started = MagicMock()

        with patch(
            "bioetl.application.composite.runner_pkg.runner.capture_runtime_timing_anchor",
            return_value=(started_at, 42.0),
        ):
            runner._start_run_lifecycle()

        assert runner._started_at == started_at
        assert runner._start_time == pytest.approx(42.0)
        runner._observer.emit_run_started.assert_called_once_with(
            composite_name="test_composite",
            run_id=runner.run_id,
        )

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

    @pytest.mark.asyncio
    async def test_records_control_plane_events_for_successful_run(self):
        """Composite runner emits ledger lifecycle events when attached."""
        checkpoint_manager = create_mock_checkpoint_manager()
        run_ledger_service = MagicMock()
        runner = create_runner(
            checkpoint_manager=checkpoint_manager,
            manifest_id="manifest-123",
            run_ledger_service=run_ledger_service,
        )

        await runner.run()

        assert runner.manifest_id == "manifest-123"
        run_ledger_service.record_run_started.assert_called_once_with()
        assert [
            call.kwargs["stage"]
            for call in run_ledger_service.record_stage_started.call_args_list
        ] == [
            COMPOSITE_RUN_LEDGER_STAGE_NAMES[0],
            COMPOSITE_RUN_LEDGER_STAGE_NAMES[2],
            COMPOSITE_RUN_LEDGER_STAGE_NAMES[3],
        ]
        assert [
            call.kwargs["stage"]
            for call in run_ledger_service.record_stage_completed.call_args_list
        ] == [
            COMPOSITE_RUN_LEDGER_STAGE_NAMES[0],
            COMPOSITE_RUN_LEDGER_STAGE_NAMES[2],
            COMPOSITE_RUN_LEDGER_STAGE_NAMES[3],
        ]
        run_ledger_service.record_run_finished.assert_called_once_with(
            metrics_snapshot={
                "records_extracted": 100,
                "records_silver": 95,
                "keys_generated": 95,
                "dependencies_total": 0,
                "dependencies_succeeded": 0,
                "dependencies_failed": 0,
                "enrichers_total": 0,
                "enrichers_succeeded": 0,
                "enrichers_failed": 0,
                "enrichers_skipped": 0,
                "records_merged": 100,
                "records_from_seed": 100,
                "records_enriched": 0,
                "records_fully_enriched": 0,
            }
        )

    @pytest.mark.asyncio
    async def test_records_composite_phase_metric_families_for_successful_run(self):
        """Composite runner emits bounded composite phase counters on success."""
        checkpoint_manager = create_mock_checkpoint_manager()
        metrics = MagicMock()
        runner = create_runner(
            checkpoint_manager=checkpoint_manager,
            metrics=metrics,
        )

        await runner.run()

        metrics.increment_counter.assert_any_call(
            "bioetl_composite_phase_records_total",
            100,
            {
                "pipeline": "composite:test_composite",
                "phase": "seed",
                "outcome": "extracted",
            },
        )
        metrics.increment_counter.assert_any_call(
            "bioetl_composite_phase_loss_total",
            5,
            {
                "pipeline": "composite:test_composite",
                "phase": "seed",
                "loss_kind": "unwritten",
            },
        )
        metrics.increment_counter.assert_any_call(
            "bioetl_composite_phase_records_total",
            100,
            {
                "pipeline": "composite:test_composite",
                "phase": "merge",
                "outcome": "merged",
            },
        )

    @pytest.mark.asyncio
    async def test_complete_successful_run_emits_terminal_success_hooks(self):
        """Composite runner finalizes success through one canonical helper seam."""
        runner = create_runner()
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=runner.run_id,
        )
        execution_context = _composite_execution_context()
        completion_context = MagicMock()
        result = MagicMock()
        runner._finalize_pipeline = AsyncMock()
        runner._prepare_composite_result_context = MagicMock(
            return_value=completion_context
        )
        runner._log_composite_completion = MagicMock()
        runner._finalize_composite_result = MagicMock(return_value=result)
        runner._record_run_finished = MagicMock()

        completed = await runner._complete_successful_run(state, execution_context)

        runner._finalize_pipeline.assert_awaited_once_with(state)
        runner._prepare_composite_result_context.assert_called_once_with(
            execution_context
        )
        runner._log_composite_completion.assert_called_once_with(completion_context)
        runner._finalize_composite_result.assert_called_once_with(completion_context)
        runner._record_run_finished.assert_called_once_with(execution_context)
        assert completed is result

    @pytest.mark.asyncio
    async def test_records_shutdown_event_for_graceful_shutdown(self):
        """Composite runner emits shutdown ledger event on graceful stop."""
        checkpoint_manager = create_mock_checkpoint_manager()
        run_ledger_service = MagicMock()
        runner = create_runner(
            checkpoint_manager=checkpoint_manager,
            manifest_id="manifest-123",
            run_ledger_service=run_ledger_service,
        )
        runner._lock.heartbeat.return_value = False

        with pytest.raises(PipelineShutdownError):
            await runner.run()

        run_ledger_service.record_run_started.assert_called_once_with()
        run_ledger_service.record_run_shutdown.assert_called_once_with(
            metrics_snapshot={}
        )
        run_ledger_service.record_run_failed.assert_not_called()
        run_ledger_service.record_run_finished.assert_not_called()


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

        deps = CompositeRunnerDependencies(
            seed_runner_factory=seed_runner_factory(seed_runner),
            enricher_runner_factory=new_enricher_runner_factory(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=checkpoint_manager,
            logger=logger,
            lock=create_mock_lock(),
            fsm_state_helper=create_mock_fsm_state_helper(logger=logger),
        )
        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(),
            deps=deps,
        )

        with pytest.raises(RuntimeError):
            await runner.run()

        # Verify error was logged
        error_calls = [
            c for c in logger.error.call_args_list if "Seed pipeline failed" in str(c)
        ]
        assert len(error_calls) >= 1, "Should log seed failure error"

    @pytest.mark.asyncio
    async def test_records_run_failed_when_seed_execution_raises(self):
        """Composite runner emits run_failed when execution aborts."""
        checkpoint_manager = create_mock_checkpoint_manager()
        run_ledger_service = MagicMock()
        runner = create_runner(
            seed_runner=MockPipelineRunner(
                should_fail=True,
                error_message="boom",
            ),
            checkpoint_manager=checkpoint_manager,
            run_ledger_service=run_ledger_service,
        )

        with pytest.raises(RuntimeError, match="boom"):
            await runner.run()

        run_ledger_service.record_run_started.assert_called_once_with()
        assert [
            call.kwargs["stage"]
            for call in run_ledger_service.record_stage_started.call_args_list
        ] == [COMPOSITE_RUN_LEDGER_STAGE_NAMES[0]]
        run_ledger_service.record_run_exception.assert_called_once()
        error = run_ledger_service.record_run_exception.call_args.kwargs["error"]
        assert isinstance(error, RuntimeError)
        assert str(error) == "boom"
        assert (
            run_ledger_service.record_run_exception.call_args.kwargs["metrics_snapshot"]
            == {}
        )
        run_ledger_service.record_run_failed.assert_not_called()


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
            created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
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
            created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
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
            created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )
        checkpoint_manager = create_mock_checkpoint_manager(initial_state)
        logger = create_mock_logger()

        deps = CompositeRunnerDependencies(
            seed_runner_factory=new_seed_runner_factory(),
            enricher_runner_factory=new_enricher_runner_factory(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=checkpoint_manager,
            logger=logger,
            lock=create_mock_lock(),
            fsm_state_helper=create_mock_fsm_state_helper(logger=logger),
        )
        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(resume=True),
            deps=deps,
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

    def test_resume_seed_phase_corrects_state_and_logs_transition(self):
        """Seed resume helper should normalize old checkpoint state and emit seed_resume transition."""
        logger = create_mock_logger()
        deps = CompositeRunnerDependencies(
            seed_runner_factory=new_seed_runner_factory(),
            enricher_runner_factory=new_enricher_runner_factory(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=create_mock_checkpoint_manager(),
            logger=logger,
            lock=create_mock_lock(),
            fsm_state_helper=create_mock_fsm_state_helper(logger=logger),
        )
        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(resume=True),
            deps=deps,
        )
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            state=CompositePipelineState.NOT_STARTED,
            seed_completed=True,
            seed_result=SeedResult(
                pipeline_name="chembl_activity",
                records_extracted=100,
                records_silver=95,
                keys_generated=90,
                duration_seconds=10.0,
            ),
            created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )

        next_state = runner._resume_seed_phase(state)

        assert next_state.state == CompositePipelineState.SEED_COMPLETED
        transition_calls = [
            c for c in logger.info.call_args_list if "FSM state transition" in str(c)
        ]
        assert any("seed_resume" in str(c) for c in transition_calls)

    @pytest.mark.asyncio
    async def test_prepare_run_state_when_resume_failed_then_normalizes_and_logs(
        self,
    ) -> None:
        """Run-state preparation should apply resume semantics before stage execution."""
        config = MockCompositeConfig()
        config.enrichers = (MagicMock(),)
        failed_state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            state=CompositePipelineState.FAILED,
            seed_completed=True,
            seed_result=SeedResult(
                pipeline_name="chembl_activity",
                records_extracted=100,
                records_silver=95,
                keys_generated=90,
                duration_seconds=10.0,
            ),
            completed_enrichers=frozenset({"crossref"}),
            created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )
        checkpoint_manager = create_mock_checkpoint_manager(failed_state)
        logger = create_mock_logger()
        run_id = str(uuid4())
        deps = CompositeRunnerDependencies(
            seed_runner_factory=new_seed_runner_factory(),
            enricher_runner_factory=new_enricher_runner_factory(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=checkpoint_manager,
            logger=logger,
            lock=create_mock_lock(),
            fsm_state_helper=create_mock_fsm_state_helper(
                logger=logger,
                config=config,
                run_id=run_id,
            ),
        )
        runner = CompositePipelineRunner(
            config=config,
            runtime=CompositeRuntimeConfig(resume=True),
            deps=deps,
            run_id=run_id,
        )

        prepared_state = await runner._prepare_run_state()

        assert prepared_state.state == CompositePipelineState.ENRICHMENT_COMPLETED
        info_calls = [str(c) for c in logger.info.call_args_list]
        assert any("Resuming from checkpoint" in c for c in info_calls)

    @pytest.mark.asyncio
    async def test_run_with_lock_when_successful_then_hands_off_named_execution_context(
        self,
    ) -> None:
        """Runner shell should hand final stage outputs to result assembly via one context."""
        runner = create_runner()
        state = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=str(uuid4()),
            created_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        )
        seed_result = SeedResult(
            pipeline_name="chembl_activity",
            records_extracted=100,
            records_silver=95,
            keys_generated=95,
            duration_seconds=1.0,
        )
        dependency_results = {
            "dep_a": DependencyResult(
                pipeline_name="dep_a",
                status=DependencyStatus.SUCCESS,
            )
        }
        enrichment_results = {
            "enricher_a": EnrichmentResult(
                enricher_name="enricher_a",
                status=EnrichmentStatus.SUCCESS,
            )
        }
        merge_result = MergeResult(
            records_merged=95,
            records_from_seed=100,
            records_enriched=10,
        )
        execution_context = CompositeExecutionContext(
            seed_result=seed_result,
            dependency_results=dependency_results,
            enrichment_results=enrichment_results,
            merge_result=merge_result,
        )
        expected_result = MagicMock(name="composite_result")

        runner._prepare_run_state = AsyncMock(return_value=state)
        runner._execute_locked_run_phases = AsyncMock(
            return_value=(state, execution_context)
        )
        runner._complete_successful_run = AsyncMock(return_value=expected_result)

        result = await runner._run_with_lock()

        assert result is expected_result
        runner._execute_locked_run_phases.assert_awaited_once_with(state)
        runner._complete_successful_run.assert_awaited_once_with(
            state,
            execution_context,
        )


class TestFSMTransitionLogging:
    """Tests for FSM transition logging."""

    @pytest.mark.asyncio
    async def test_seed_start_transition_logged(self):
        """Transition to SEED_RUNNING should be logged."""
        logger = create_mock_logger()
        deps = CompositeRunnerDependencies(
            seed_runner_factory=new_seed_runner_factory(),
            enricher_runner_factory=new_enricher_runner_factory(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=create_mock_checkpoint_manager(),
            logger=logger,
            lock=create_mock_lock(),
            fsm_state_helper=create_mock_fsm_state_helper(logger=logger),
        )
        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(),
            deps=deps,
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
        deps = CompositeRunnerDependencies(
            seed_runner_factory=new_seed_runner_factory(),
            enricher_runner_factory=new_enricher_runner_factory(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=create_mock_checkpoint_manager(),
            logger=logger,
            lock=create_mock_lock(),
            fsm_state_helper=create_mock_fsm_state_helper(logger=logger),
        )
        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(),
            deps=deps,
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
        deps = CompositeRunnerDependencies(
            seed_runner_factory=seed_runner_factory(seed_runner),
            enricher_runner_factory=new_enricher_runner_factory(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=create_mock_checkpoint_manager(),
            logger=logger,
            lock=create_mock_lock(),
            fsm_state_helper=create_mock_fsm_state_helper(logger=logger),
        )
        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(),
            deps=deps,
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
            side_effect=[StorageError("Disk full"), None, None, None, None, None]
        )
        logger = create_mock_logger()

        deps = CompositeRunnerDependencies(
            seed_runner_factory=new_seed_runner_factory(),
            enricher_runner_factory=new_enricher_runner_factory(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=checkpoint_manager,
            logger=logger,
            lock=create_mock_lock(),
            fsm_state_helper=create_mock_fsm_state_helper(logger=logger),
        )
        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(),
            deps=deps,
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

        deps = CompositeRunnerDependencies(
            seed_runner_factory=new_seed_runner_factory(),
            enricher_runner_factory=new_enricher_runner_factory(),
            key_extractor=create_mock_key_extractor(),
            coordinator=create_mock_coordinator(),
            merger=create_mock_merger(),
            checkpoint_manager=checkpoint_manager,
            logger=logger,
            lock=create_mock_lock(),
            fsm_state_helper=create_mock_fsm_state_helper(logger=logger),
        )
        runner = CompositePipelineRunner(
            config=MockCompositeConfig(),
            runtime=CompositeRuntimeConfig(),
            deps=deps,
        )

        await runner.run()

        # Verify warning logged with correct context
        warning_calls = logger.warning.call_args_list
        assert any("checkpoint_save_failed" in str(c) for c in warning_calls)
        assert any("Permission denied" in str(c) for c in warning_calls)
