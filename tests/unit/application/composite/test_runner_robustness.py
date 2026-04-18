"""Unit tests for CompositePipelineRunner robustness and error handling.

Tests for FSM error handling, double execution protection, configuration
consistency validation, and edge cases.

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import polars as pl
import pytest

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointState,
)
from bioetl.application.composite.runner_pkg import (
    CompositePipelineRunner,
    CompositeRunnerDependencies,
    CompositeRuntimeConfig,
)
from bioetl.domain.composite.result import (
    EnrichmentResult,
    MergeResult,
    SeedResult,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import RunnerAlreadyExecutedError
from tests.unit.application.composite import runner_test_support as support

InMemoryCheckpointManager = support.InMemoryCheckpointManager
create_checkpoint_manager = support.create_in_memory_checkpoint_manager


def _seed_runner_factory(seed_runner: AsyncMock):
    return support.seed_runner_factory(seed_runner)


def _new_enricher_runner_factory():
    def _factory(name: str, df: object) -> AsyncMock:
        return AsyncMock()

    return _factory


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def test_run_id() -> str:
    """Generate a valid UUID for test run ID."""
    return str(uuid4())


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger."""
    return support.create_mock_logger()


@pytest.fixture
def mock_lock() -> AsyncMock:
    """Create a mock lock."""
    return support.create_mock_lock()


@pytest.fixture
def mock_merger() -> AsyncMock:
    """Create a mock merger service."""
    return support.create_mock_merger(
        MergeResult(
            records_from_seed=100,
            records_merged=95,
            records_enriched=80,
            records_fully_enriched=70,
            sources_used=("crossref", "pubmed"),
            output_silver_path="silver/composite/test",
            output_gold_path="gold/test_enriched",
            duration_seconds=5.0,
        )
    )


@pytest.fixture
def mock_coordinator() -> AsyncMock:
    """Create a mock enrichment coordinator."""
    return support.create_mock_coordinator(
        {
            "crossref": EnrichmentResult.success(
                enricher_name="crossref",
                records_input=100,
                records_enriched=95,
                records_not_found=5,
                duration_seconds=10.0,
            ),
        }
    )


@pytest.fixture
def mock_key_extractor() -> AsyncMock:
    """Create a mock key extractor service."""
    return support.create_mock_key_extractor(pl.DataFrame({"doi": ["10.1234/test"]}))


@pytest.fixture
def mock_seed_runner() -> AsyncMock:
    """Create a mock seed runner."""
    return support.create_async_seed_runner()


@pytest.fixture
def mock_config() -> MagicMock:
    """Create a mock composite config."""
    return support.create_magic_composite_config(output_keys=("doi",))


def create_runner(
    mock_config: MagicMock,
    mock_logger: MagicMock,
    mock_lock: AsyncMock,
    mock_merger: AsyncMock,
    mock_coordinator: AsyncMock,
    mock_key_extractor: AsyncMock,
    mock_seed_runner: AsyncMock,
    checkpoint_manager: InMemoryCheckpointManager,
    test_run_id: str,
    runtime: CompositeRuntimeConfig | None = None,
    preflight_validator: MagicMock | None = None,
) -> CompositePipelineRunner:
    """Helper to create a runner with all dependencies."""
    deps = CompositeRunnerDependencies(
        seed_runner_factory=_seed_runner_factory(mock_seed_runner),
        enricher_runner_factory=_new_enricher_runner_factory(),
        key_extractor=mock_key_extractor,
        coordinator=mock_coordinator,
        merger=mock_merger,
        checkpoint_manager=checkpoint_manager,
        logger=mock_logger,
        lock=mock_lock,
        fsm_state_helper=MagicMock(),
        preflight_validator=preflight_validator,
    )
    return CompositePipelineRunner(
        config=mock_config,
        runtime=runtime or CompositeRuntimeConfig(dry_run=False),
        deps=deps,
        run_id=test_run_id,
    )


# ============================================================================
# Double Execution Protection Tests
# ============================================================================


class TestDoubleExecutionProtection:
    """Tests for protection against running the same Runner twice."""

    @pytest.mark.asyncio
    async def test_double_run_raises_error(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Running the same Runner twice should raise RunnerAlreadyExecutedError."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )

        runner = create_runner(
            mock_config=mock_config,
            mock_logger=mock_logger,
            mock_lock=mock_lock,
            mock_merger=mock_merger,
            mock_coordinator=mock_coordinator,
            mock_key_extractor=mock_key_extractor,
            mock_seed_runner=mock_seed_runner,
            checkpoint_manager=checkpoint_manager,
            test_run_id=test_run_id,
        )

        # First run should succeed
        result = await runner.run()
        assert result is not None
        assert result.composite_name == "test_composite"

        # Second run should raise RunnerAlreadyExecutedError
        with pytest.raises(RunnerAlreadyExecutedError) as exc_info:
            await runner.run()

        assert exc_info.value.runner_type == "CompositePipelineRunner"
        assert exc_info.value.run_id == test_run_id
        assert exc_info.value.final_state == "completed"

    @pytest.mark.asyncio
    async def test_double_run_after_failure_raises_error(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Running a Runner again after failure should also raise error."""
        # Make merge fail
        mock_merger.merge.side_effect = RuntimeError("Merge failed")

        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )

        runner = create_runner(
            mock_config=mock_config,
            mock_logger=mock_logger,
            mock_lock=mock_lock,
            mock_merger=mock_merger,
            mock_coordinator=mock_coordinator,
            mock_key_extractor=mock_key_extractor,
            mock_seed_runner=mock_seed_runner,
            checkpoint_manager=checkpoint_manager,
            test_run_id=test_run_id,
        )

        # First run should fail
        with pytest.raises(RuntimeError, match="Merge failed"):
            await runner.run()

        # Second run should raise RunnerAlreadyExecutedError
        with pytest.raises(RunnerAlreadyExecutedError) as exc_info:
            await runner.run()

        assert exc_info.value.final_state == "failed"

    @pytest.mark.asyncio
    async def test_error_message_includes_state(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Error message should include helpful context."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )

        runner = create_runner(
            mock_config=mock_config,
            mock_logger=mock_logger,
            mock_lock=mock_lock,
            mock_merger=mock_merger,
            mock_coordinator=mock_coordinator,
            mock_key_extractor=mock_key_extractor,
            mock_seed_runner=mock_seed_runner,
            checkpoint_manager=checkpoint_manager,
            test_run_id=test_run_id,
        )

        await runner.run()

        with pytest.raises(RunnerAlreadyExecutedError) as exc_info:
            await runner.run()

        error_message = str(exc_info.value)
        assert "CompositePipelineRunner" in error_message
        assert test_run_id in error_message
        assert "Create a new Runner instance" in error_message


# ============================================================================
# FSM Transition Validation Tests
# ============================================================================


class TestFSMTransitionValidation:
    """Tests for FSM transition validation."""

    @pytest.mark.asyncio
    async def test_valid_transitions_do_not_log_warning(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Valid FSM transitions should not log warnings."""
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )

        runner = create_runner(
            mock_config=mock_config,
            mock_logger=mock_logger,
            mock_lock=mock_lock,
            mock_merger=mock_merger,
            mock_coordinator=mock_coordinator,
            mock_key_extractor=mock_key_extractor,
            mock_seed_runner=mock_seed_runner,
            checkpoint_manager=checkpoint_manager,
            test_run_id=test_run_id,
        )

        await runner.run()

        # Check that no warning about "Invalid FSM transition" was logged
        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args and "Invalid FSM transition" in str(c.args[0])
        ]
        assert len(warning_calls) == 0, "No invalid FSM transition warnings expected"

    @pytest.mark.asyncio
    async def test_resume_from_failed_uses_allow_resume_flag(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Resume from FAILED should use allow_resume flag and not warn."""
        # Create a checkpoint in FAILED state
        failed_checkpoint = CompositeCheckpointState(
            composite_name="test_composite",
            run_id=test_run_id,
            state=CompositePipelineState.FAILED,
            seed_completed=True,
            seed_result=SeedResult(
                pipeline_name="chembl_activity",
                records_extracted=100,
                records_silver=95,
                keys_generated=90,
                duration_seconds=10.0,
            ),
            completed_enrichers=frozenset(),
            enrichment_results={},
            created_at=datetime.now(tz=UTC),
        )

        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=True,
        )
        await checkpoint_manager.save(failed_checkpoint)

        runner = create_runner(
            mock_config=mock_config,
            mock_logger=mock_logger,
            mock_lock=mock_lock,
            mock_merger=mock_merger,
            mock_coordinator=mock_coordinator,
            mock_key_extractor=mock_key_extractor,
            mock_seed_runner=mock_seed_runner,
            checkpoint_manager=checkpoint_manager,
            test_run_id=test_run_id,
            runtime=CompositeRuntimeConfig(resume=True),
        )

        await runner.run()

        # Should NOT have warnings about invalid transitions from FAILED
        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args and "Invalid FSM transition" in str(c.args[0])
        ]
        assert len(warning_calls) == 0, "Resume from FAILED should not warn"


# ============================================================================
# Configuration Consistency Tests
# ============================================================================


class TestConfigurationConsistency:
    """Tests for configuration consistency validation."""

    @pytest.mark.asyncio
    async def test_all_optional_enrichers_logs_info(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """When all enrichers are optional, should log info message."""
        # Configure with optional enrichers only
        enricher1 = MagicMock()
        enricher1.pipeline = "crossref"
        enricher1.required = False
        mock_config.enrichers = [enricher1]
        mock_config.required_enrichers = []

        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )

        runner = create_runner(
            mock_config=mock_config,
            mock_logger=mock_logger,
            mock_lock=mock_lock,
            mock_merger=mock_merger,
            mock_coordinator=mock_coordinator,
            mock_key_extractor=mock_key_extractor,
            mock_seed_runner=mock_seed_runner,
            checkpoint_manager=checkpoint_manager,
            test_run_id=test_run_id,
        )

        await runner.run()

        # Check that info message about all optional enrichers was logged
        info_calls = [
            c
            for c in mock_logger.info.call_args_list
            if c.args and "All enrichers are optional" in str(c.args[0])
        ]
        assert len(info_calls) == 1, "Should log info about all optional enrichers"

    @pytest.mark.asyncio
    async def test_required_enrichers_consistency_warning(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Mismatch in required_enrichers should log warning."""
        # Create inconsistent config: enricher says required, but required_enrichers list empty
        enricher1 = MagicMock()
        enricher1.pipeline = "crossref"
        enricher1.required = True  # Enricher is marked required
        mock_config.enrichers = [enricher1]
        mock_config.required_enrichers = []  # But required_enrichers is empty (inconsistent!)

        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )

        runner = create_runner(
            mock_config=mock_config,
            mock_logger=mock_logger,
            mock_lock=mock_lock,
            mock_merger=mock_merger,
            mock_coordinator=mock_coordinator,
            mock_key_extractor=mock_key_extractor,
            mock_seed_runner=mock_seed_runner,
            checkpoint_manager=checkpoint_manager,
            test_run_id=test_run_id,
        )

        await runner.run()

        # Check that warning about inconsistency was logged
        warning_calls = [
            c
            for c in mock_logger.warning.call_args_list
            if c.args and "required_enrichers mismatch" in str(c.args[0])
        ]
        assert len(warning_calls) == 1, (
            "Should log warning about required_enrichers mismatch"
        )


class TestPreflightSkipPolicy:
    """Tests for preflight gating policy."""

    def test_missing_validator_returns_skip_reason(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Missing validator should skip preflight explicitly."""
        mock_config.merge.field_priorities = ["doi"]
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        runner = create_runner(
            mock_config=mock_config,
            mock_logger=mock_logger,
            mock_lock=mock_lock,
            mock_merger=mock_merger,
            mock_coordinator=mock_coordinator,
            mock_key_extractor=mock_key_extractor,
            mock_seed_runner=mock_seed_runner,
            checkpoint_manager=checkpoint_manager,
            test_run_id=test_run_id,
        )

        assert (
            runner._get_preflight_skip_reason() == "preflight_validator not configured"
        )

    def test_empty_field_priorities_returns_skip_reason(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Empty field priorities should skip preflight explicitly."""
        mock_config.merge.field_priorities = []
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        runner = create_runner(
            mock_config=mock_config,
            mock_logger=mock_logger,
            mock_lock=mock_lock,
            mock_merger=mock_merger,
            mock_coordinator=mock_coordinator,
            mock_key_extractor=mock_key_extractor,
            mock_seed_runner=mock_seed_runner,
            checkpoint_manager=checkpoint_manager,
            test_run_id=test_run_id,
            preflight_validator=MagicMock(),
        )

        assert runner._get_preflight_skip_reason() == "no field_priorities configured"

    def test_ready_preflight_returns_none(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Configured validator and field priorities should allow preflight."""
        mock_config.merge.field_priorities = ["doi"]
        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )
        runner = create_runner(
            mock_config=mock_config,
            mock_logger=mock_logger,
            mock_lock=mock_lock,
            mock_merger=mock_merger,
            mock_coordinator=mock_coordinator,
            mock_key_extractor=mock_key_extractor,
            mock_seed_runner=mock_seed_runner,
            checkpoint_manager=checkpoint_manager,
            test_run_id=test_run_id,
            preflight_validator=MagicMock(),
        )

        assert runner._get_preflight_skip_reason() is None


# ============================================================================
# Edge Cases Tests
# ============================================================================


class TestEdgeCases:
    """Tests for edge cases and unusual scenarios."""

    @pytest.mark.asyncio
    async def test_no_enrichers_still_completes(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """Pipeline with no enrichers should still complete successfully."""
        mock_config.enrichers = []
        mock_config.required_enrichers = []
        mock_coordinator.run_enrichers.return_value = {}

        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )

        runner = create_runner(
            mock_config=mock_config,
            mock_logger=mock_logger,
            mock_lock=mock_lock,
            mock_merger=mock_merger,
            mock_coordinator=mock_coordinator,
            mock_key_extractor=mock_key_extractor,
            mock_seed_runner=mock_seed_runner,
            checkpoint_manager=checkpoint_manager,
            test_run_id=test_run_id,
        )

        result = await runner.run()

        assert result is not None
        assert result.enrichment_results == {}

    @pytest.mark.asyncio
    async def test_required_only_with_no_required_enrichers(
        self,
        mock_config: MagicMock,
        mock_logger: MagicMock,
        mock_lock: AsyncMock,
        mock_merger: AsyncMock,
        mock_coordinator: AsyncMock,
        mock_key_extractor: AsyncMock,
        mock_seed_runner: AsyncMock,
        test_run_id: str,
    ) -> None:
        """required_only=True with no required enrichers should skip all."""
        enricher1 = MagicMock()
        enricher1.pipeline = "crossref"
        enricher1.required = False
        mock_config.enrichers = [enricher1]
        mock_config.required_enrichers = []
        mock_coordinator.run_enrichers.return_value = {}

        checkpoint_manager = create_checkpoint_manager(
            composite_name="test_composite",
            run_id=test_run_id,
            logger=mock_logger,
            resume=False,
        )

        runner = create_runner(
            mock_config=mock_config,
            mock_logger=mock_logger,
            mock_lock=mock_lock,
            mock_merger=mock_merger,
            mock_coordinator=mock_coordinator,
            mock_key_extractor=mock_key_extractor,
            mock_seed_runner=mock_seed_runner,
            checkpoint_manager=checkpoint_manager,
            test_run_id=test_run_id,
            runtime=CompositeRuntimeConfig(required_only=True),
        )

        result = await runner.run()

        # Pipeline should complete successfully
        assert result is not None
        # Should have NOT_RUN result for optional enricher
        assert "crossref" in result.enrichment_results
        assert result.enrichment_results["crossref"].status.value == "not_run"


# ============================================================================
# RunnerAlreadyExecutedError Tests
# ============================================================================


class TestRunnerAlreadyExecutedError:
    """Tests for RunnerAlreadyExecutedError exception."""

    def test_error_attributes(self) -> None:
        """Error should have correct attributes."""
        error = RunnerAlreadyExecutedError(
            runner_type="CompositePipelineRunner",
            run_id="test-run-123",
            final_state="completed",
        )

        assert error.runner_type == "CompositePipelineRunner"
        assert error.run_id == "test-run-123"
        assert error.final_state == "completed"

    def test_error_message_format(self) -> None:
        """Error message should be informative."""
        error = RunnerAlreadyExecutedError(
            runner_type="CompositePipelineRunner",
            run_id="test-run-123",
            final_state="failed",
        )

        msg = str(error)
        assert "CompositePipelineRunner" in msg
        assert "test-run-123" in msg
        assert "failed" in msg
        assert "Create a new Runner instance" in msg

    def test_error_without_final_state(self) -> None:
        """Error should handle missing final_state."""
        error = RunnerAlreadyExecutedError(
            runner_type="CompositePipelineRunner",
            run_id="test-run-123",
            final_state=None,
        )

        msg = str(error)
        assert "CompositePipelineRunner" in msg
        assert "test-run-123" in msg
        assert "final_state" not in msg  # Should not appear if None
