"""Unit tests for CompositePipelineRunner FSM enrichment transitions.

Tests FSM state transitions during enrichment stage:
- NOT_STARTED -> SEED_COMPLETED -> ENRICHING -> ENRICHMENT_COMPLETED -> MERGING -> COMPLETED
- ENRICHING -> FAILED (when required enricher fails)
- Skip ENRICHING when no enrichers to run.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock

import pytest

from bioetl.application.composite.runner_pkg import (
    CompositeRuntimeConfig,
)
from bioetl.application.composite.runner_pkg.runner_helpers import (
    log_enrichment_summary,
)
from bioetl.domain.composite.result import (
    EnrichmentResult,
    EnrichmentStatus,
)
from bioetl.domain.composite.state import CompositePipelineState
from bioetl.domain.exceptions import InvalidStateError, StorageError
from tests.unit.application.composite import runner_test_support as support

pytest_plugins = ("tests.unit.application.composite.fsm_test_support",)

if TYPE_CHECKING:
    from bioetl.application.composite.checkpoint.state import (
        CompositeCheckpointState,
    )


@pytest.mark.unit
class TestEnrichmentFSMTransitions:
    """Tests for FSM state transitions during enrichment stage."""

    @pytest.mark.asyncio
    async def test_transitions_to_enriching_before_enrichments(
        self, runner, mock_checkpoint_manager
    ):
        """Test FSM transitions to ENRICHING before running enrichers."""
        await runner.run()

        # Check saved states include ENRICHING
        saved_states = mock_checkpoint_manager._saved_states
        enriching_states = [
            s for s in saved_states if s.state == CompositePipelineState.ENRICHING
        ]
        assert len(enriching_states) >= 1, "Should transition to ENRICHING"

    @pytest.mark.asyncio
    async def test_enrichment_checkpoint_save_failure_is_non_fatal(
        self,
        runner,
        mock_checkpoint_manager,
        mock_logger,
    ) -> None:
        """Enrichment checkpoint save failures should degrade gracefully."""
        saved_states: list[CompositeCheckpointState] = []
        failed_once = False

        async def save_impl(state: CompositeCheckpointState) -> None:
            await asyncio.sleep(0)
            nonlocal failed_once
            saved_states.append(state)
            if state.state == CompositePipelineState.ENRICHING and not failed_once:
                failed_once = True
                raise StorageError("enrichment checkpoint unavailable")

        mock_checkpoint_manager.save = AsyncMock(side_effect=save_impl)

        result = await runner.run()

        assert result is not None
        assert any(
            "checkpoint_save_failed" in str(call)
            and "enrichment checkpoint unavailable" in str(call)
            for call in mock_logger.warning.call_args_list
        )
        assert any(
            state.state == CompositePipelineState.ENRICHMENT_COMPLETED
            for state in saved_states
        ), "Pipeline should continue past ENRICHING after checkpoint save failure"

    @pytest.mark.asyncio
    async def test_transitions_to_enrichment_completed_after_success(
        self, runner, mock_checkpoint_manager
    ):
        """Test FSM transitions to ENRICHMENT_COMPLETED after successful enrichments."""
        await runner.run()

        # Check saved states include ENRICHMENT_COMPLETED
        saved_states = mock_checkpoint_manager._saved_states
        completed_states = [
            s
            for s in saved_states
            if s.state == CompositePipelineState.ENRICHMENT_COMPLETED
        ]
        assert len(completed_states) >= 1, "Should transition to ENRICHMENT_COMPLETED"

    @pytest.mark.asyncio
    async def test_transitions_to_merging_before_merge(
        self, runner, mock_checkpoint_manager
    ):
        """Test FSM transitions to MERGING before merge operation."""
        await runner.run()

        # Check saved states include MERGING
        saved_states = mock_checkpoint_manager._saved_states
        merging_states = [
            s for s in saved_states if s.state == CompositePipelineState.MERGING
        ]
        assert len(merging_states) >= 1, "Should transition to MERGING"

    @pytest.mark.asyncio
    async def test_state_transition_order(self, runner, mock_checkpoint_manager):
        """Test FSM state transitions occur in correct order."""
        await runner.run()

        saved_states = mock_checkpoint_manager._saved_states
        state_sequence = [s.state for s in saved_states]

        # Find indices of key states
        def find_state_index(state: CompositePipelineState) -> int:
            for i, s in enumerate(state_sequence):
                if s == state:
                    return i
            return -1

        seed_completed_idx = find_state_index(CompositePipelineState.SEED_COMPLETED)
        enriching_idx = find_state_index(CompositePipelineState.ENRICHING)
        enrichment_completed_idx = find_state_index(
            CompositePipelineState.ENRICHMENT_COMPLETED
        )
        merging_idx = find_state_index(CompositePipelineState.MERGING)

        # Verify order: SEED_COMPLETED < ENRICHING < ENRICHMENT_COMPLETED < MERGING
        assert seed_completed_idx >= 0, "SEED_COMPLETED should be saved"
        assert enriching_idx >= 0, "ENRICHING should be saved"
        assert enrichment_completed_idx >= 0, "ENRICHMENT_COMPLETED should be saved"
        assert merging_idx >= 0, "MERGING should be saved"

        assert seed_completed_idx < enriching_idx, (
            "SEED_COMPLETED should come before ENRICHING"
        )
        assert enriching_idx < enrichment_completed_idx, (
            "ENRICHING should come before ENRICHMENT_COMPLETED"
        )
        assert enrichment_completed_idx < merging_idx, (
            "ENRICHMENT_COMPLETED should come before MERGING"
        )


@pytest.mark.unit
class TestEnrichmentFSMFailure:
    """Tests for FSM FAILED state transition when required enricher fails."""

    @pytest.mark.asyncio
    async def test_transitions_to_failed_when_required_enricher_fails(
        self,
        sample_composite_config,
        mock_seed_runner_factory,
        mock_enricher_runner_factory,
        mock_key_extractor,
        mock_merger,
        mock_checkpoint_manager,
        mock_logger,
        mock_lock,
    ):
        """Test FSM transitions to FAILED when required enricher fails."""
        # Setup coordinator to return failed result for required enricher
        mock_coordinator = AsyncMock()
        mock_coordinator.run_enrichers = AsyncMock(
            return_value={
                "crossref": EnrichmentResult.failed(
                    enricher_name="crossref",
                    error_message="Connection timeout",
                    records_input=2,
                ),
            }
        )

        runner = support.create_runner(
            config=sample_composite_config,
            runtime=CompositeRuntimeConfig(resume=False, dry_run=False),
            logger=mock_logger,
            checkpoint_manager=mock_checkpoint_manager,
            seed_runner_factory=mock_seed_runner_factory,
            enricher_runner_factory=mock_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            lock=mock_lock,
            run_id="00000000-0000-0000-0000-000000000123",
        )

        with pytest.raises(
            InvalidStateError, match="Required enricher 'crossref' failed"
        ):
            await runner.run()

        # Check FAILED state was saved
        saved_states = mock_checkpoint_manager._saved_states
        failed_states = [
            s for s in saved_states if s.state == CompositePipelineState.FAILED
        ]
        assert len(failed_states) >= 1, "Should transition to FAILED"

    @pytest.mark.asyncio
    async def test_failed_state_saved_before_exception_raised(
        self,
        sample_composite_config,
        mock_seed_runner_factory,
        mock_enricher_runner_factory,
        mock_key_extractor,
        mock_merger,
        mock_checkpoint_manager,
        mock_logger,
        mock_lock,
    ):
        """Test FAILED state is saved before InvalidStateError is raised."""
        mock_coordinator = AsyncMock()
        mock_coordinator.run_enrichers = AsyncMock(
            return_value={
                "crossref": EnrichmentResult.failed(
                    enricher_name="crossref",
                    error_message="DQ threshold exceeded",
                    records_input=100,
                ),
            }
        )

        runner = support.create_runner(
            config=sample_composite_config,
            runtime=CompositeRuntimeConfig(resume=False, dry_run=False),
            logger=mock_logger,
            checkpoint_manager=mock_checkpoint_manager,
            seed_runner_factory=mock_seed_runner_factory,
            enricher_runner_factory=mock_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            lock=mock_lock,
            run_id="00000000-0000-0000-0000-000000000123",
        )

        with pytest.raises(InvalidStateError):
            await runner.run()

        # Verify checkpoint.save was called with FAILED state
        saved_states = mock_checkpoint_manager._saved_states
        assert any(s.state == CompositePipelineState.FAILED for s in saved_states), (
            "FAILED state must be saved"
        )

    @pytest.mark.asyncio
    async def test_logs_error_when_required_enricher_fails(
        self,
        sample_composite_config,
        mock_seed_runner_factory,
        mock_enricher_runner_factory,
        mock_key_extractor,
        mock_merger,
        mock_checkpoint_manager,
        mock_logger,
        mock_lock,
    ):
        """Test error is logged when required enricher fails."""
        mock_coordinator = AsyncMock()
        mock_coordinator.run_enrichers = AsyncMock(
            return_value={
                "crossref": EnrichmentResult.failed(
                    enricher_name="crossref",
                    error_message="API error",
                    records_input=10,
                ),
            }
        )

        runner = support.create_runner(
            config=sample_composite_config,
            runtime=CompositeRuntimeConfig(resume=False, dry_run=False),
            logger=mock_logger,
            checkpoint_manager=mock_checkpoint_manager,
            seed_runner_factory=mock_seed_runner_factory,
            enricher_runner_factory=mock_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            lock=mock_lock,
            run_id="00000000-0000-0000-0000-000000000123",
        )

        with pytest.raises(InvalidStateError):
            await runner.run()

        # Verify error was logged with FAILED state
        mock_logger.error.assert_called()
        error_calls = [
            c
            for c in mock_logger.error.call_args_list
            if "FAILED" in str(c) or "failed" in str(c).lower()
        ]
        assert len(error_calls) >= 1, "Should log error about FAILED state"


@pytest.mark.unit
class TestEnrichmentSkipStage:
    """Tests for skipping enrichment stage when no enrichers to run."""

    @pytest.mark.asyncio
    async def test_skips_enriching_when_no_enrichers(
        self,
        sample_composite_config,
        mock_seed_runner_factory,
        mock_enricher_runner_factory,
        mock_key_extractor,
        mock_coordinator,
        mock_merger,
        mock_checkpoint_manager,
        mock_logger,
        mock_lock,
    ):
        """Test ENRICHING stage is skipped when no enrichers to run."""
        # Configure no enrichers
        sample_composite_config.enrichers = []
        sample_composite_config.required_enrichers = []

        runner = support.create_runner(
            config=sample_composite_config,
            runtime=CompositeRuntimeConfig(resume=False, dry_run=False),
            logger=mock_logger,
            checkpoint_manager=mock_checkpoint_manager,
            seed_runner_factory=mock_seed_runner_factory,
            enricher_runner_factory=mock_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            lock=mock_lock,
            run_id="00000000-0000-0000-0000-000000000123",
        )

        await runner.run()

        # Coordinator should not be called
        mock_coordinator.run_enrichers.assert_not_called()

        # Should log skip message
        skip_calls = [
            c
            for c in mock_logger.info.call_args_list
            if "skipping" in str(c).lower() or "No enrichers" in str(c)
        ]
        assert len(skip_calls) >= 1, "Should log that enrichment stage is skipped"

    @pytest.mark.asyncio
    async def test_transitions_directly_to_enrichment_completed_when_no_enrichers(
        self,
        sample_composite_config,
        mock_seed_runner_factory,
        mock_enricher_runner_factory,
        mock_key_extractor,
        mock_coordinator,
        mock_merger,
        mock_checkpoint_manager,
        mock_logger,
        mock_lock,
    ):
        """Test FSM transitions to ENRICHMENT_COMPLETED when no enrichers."""
        sample_composite_config.enrichers = []
        sample_composite_config.required_enrichers = []

        runner = support.create_runner(
            config=sample_composite_config,
            runtime=CompositeRuntimeConfig(resume=False, dry_run=False),
            logger=mock_logger,
            checkpoint_manager=mock_checkpoint_manager,
            seed_runner_factory=mock_seed_runner_factory,
            enricher_runner_factory=mock_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            lock=mock_lock,
            run_id="00000000-0000-0000-0000-000000000123",
        )

        await runner.run()

        # Should still reach ENRICHMENT_COMPLETED and MERGING
        saved_states = mock_checkpoint_manager._saved_states
        state_values = [s.state for s in saved_states]

        assert CompositePipelineState.ENRICHMENT_COMPLETED in state_values
        assert CompositePipelineState.MERGING in state_values


@pytest.mark.unit
class TestOptionalEnricherFailure:
    """Tests for optional enricher failure handling."""

    @pytest.mark.asyncio
    async def test_continues_when_optional_enricher_fails(
        self,
        sample_composite_config,
        mock_seed_runner_factory,
        mock_enricher_runner_factory,
        mock_key_extractor,
        mock_merger,
        mock_checkpoint_manager,
        mock_logger,
        mock_lock,
    ):
        """Test pipeline continues when optional enricher fails."""
        # Configure with optional enricher only
        optional_enricher = MagicMock()
        optional_enricher.pipeline = "pubmed"
        optional_enricher.required = False
        optional_enricher.silver_table = "silver/pubmed/publication"

        sample_composite_config.enrichers = [optional_enricher]
        sample_composite_config.required_enrichers = []

        mock_coordinator = AsyncMock()
        mock_coordinator.run_enrichers = AsyncMock(
            return_value={
                "pubmed": EnrichmentResult.failed(
                    enricher_name="pubmed",
                    error_message="Rate limit exceeded",
                    records_input=100,
                ),
            }
        )

        runner = support.create_runner(
            config=sample_composite_config,
            runtime=CompositeRuntimeConfig(resume=False, dry_run=False),
            logger=mock_logger,
            checkpoint_manager=mock_checkpoint_manager,
            seed_runner_factory=mock_seed_runner_factory,
            enricher_runner_factory=mock_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            lock=mock_lock,
            run_id="00000000-0000-0000-0000-000000000123",
        )

        # Should NOT raise
        result = await runner.run()

        # Should complete successfully
        assert result is not None
        assert result.composite_name == "test_composite"

        # Should reach ENRICHMENT_COMPLETED and MERGING
        saved_states = mock_checkpoint_manager._saved_states
        state_values = [s.state for s in saved_states]
        assert CompositePipelineState.ENRICHMENT_COMPLETED in state_values
        assert CompositePipelineState.MERGING in state_values

    @pytest.mark.asyncio
    async def test_required_success_optional_failure_succeeds(
        self,
        sample_composite_config,
        mock_seed_runner_factory,
        mock_enricher_runner_factory,
        mock_key_extractor,
        mock_merger,
        mock_checkpoint_manager,
        mock_logger,
        mock_lock,
    ):
        """Test pipeline succeeds when required enricher succeeds but optional fails."""
        # Configure with both required and optional enrichers
        required_enricher = MagicMock()
        required_enricher.pipeline = "crossref"
        required_enricher.required = True
        required_enricher.silver_table = "silver/crossref/publication"

        optional_enricher = MagicMock()
        optional_enricher.pipeline = "pubmed"
        optional_enricher.required = False
        optional_enricher.silver_table = "silver/pubmed/publication"

        sample_composite_config.enrichers = [required_enricher, optional_enricher]
        sample_composite_config.required_enrichers = ["crossref"]

        mock_coordinator = AsyncMock()
        mock_coordinator.run_enrichers = AsyncMock(
            return_value={
                "crossref": EnrichmentResult.success(
                    enricher_name="crossref",
                    records_input=100,
                    records_enriched=95,
                    records_not_found=5,
                    duration_seconds=10.0,
                ),
                "pubmed": EnrichmentResult.failed(
                    enricher_name="pubmed",
                    error_message="API error",
                    records_input=100,
                ),
            }
        )

        runner = support.create_runner(
            config=sample_composite_config,
            runtime=CompositeRuntimeConfig(resume=False, dry_run=False),
            logger=mock_logger,
            checkpoint_manager=mock_checkpoint_manager,
            seed_runner_factory=mock_seed_runner_factory,
            enricher_runner_factory=mock_enricher_runner_factory,
            key_extractor=mock_key_extractor,
            coordinator=mock_coordinator,
            merger=mock_merger,
            lock=mock_lock,
            run_id="00000000-0000-0000-0000-000000000123",
        )

        result = await runner.run()

        # Should complete successfully
        assert result is not None
        assert "crossref" in result.enrichment_results
        assert "pubmed" in result.enrichment_results
        assert result.enrichment_results["crossref"].is_success
        assert not result.enrichment_results["pubmed"].is_success


@pytest.mark.unit
class TestEnrichmentLogging:
    """Tests for enrichment stage logging."""

    @pytest.mark.asyncio
    async def test_logs_enrichment_stage_started(self, runner, mock_logger):
        """Test logging when enrichment stage starts."""
        await runner.run()

        # Find log call with enriching state (lowercase) or phase event
        enriching_calls = [
            c
            for c in mock_logger.info.call_args_list
            if "enriching" in str(c).lower() or "enrichment_started" in str(c)
        ]
        assert len(enriching_calls) >= 1

    @pytest.mark.asyncio
    async def test_logs_enrichment_stage_completed(self, runner, mock_logger):
        """Test logging when enrichment stage completes."""
        await runner.run()

        # Find log call with enrichment_completed (lowercase) or phase event
        completed_calls = [
            c
            for c in mock_logger.info.call_args_list
            if "enrichment_completed" in str(c).lower()
        ]
        assert len(completed_calls) >= 1

    @pytest.mark.asyncio
    async def test_logs_enrichment_summary(self, runner, mock_logger):
        """Test logging of enrichment summary."""
        await runner.run()

        # Find log call with enrichment summary
        summary_calls = [
            c
            for c in mock_logger.info.call_args_list
            if "Enrichment summary" in str(c) or "success" in str(c).lower()
        ]
        assert len(summary_calls) >= 1


@pytest.mark.unit
class TestEnrichmentSummaryAggregation:
    """Tests for log_enrichment_summary helper function."""

    def test_log_enrichment_summary_counts_statuses(self, runner, mock_logger):
        """Test log_enrichment_summary correctly counts statuses."""
        results = {
            "enricher1": EnrichmentResult.success(
                enricher_name="enricher1",
                records_input=100,
                records_enriched=95,
                records_not_found=5,
                duration_seconds=10.0,
            ),
            "enricher2": EnrichmentResult(
                enricher_name="enricher2",
                status=EnrichmentStatus.PARTIAL,
                records_input=100,
                records_enriched=50,
                records_not_found=30,
                records_errored=20,
            ),
            "enricher3": EnrichmentResult.failed(
                enricher_name="enricher3",
                error_message="Error",
                records_input=100,
            ),
            "enricher4": EnrichmentResult.skipped(
                enricher_name="enricher4",
                reason="No data",
            ),
        }

        log_enrichment_summary(results, runner._config.name, mock_logger)

        # Verify logger.info was called with summary
        mock_logger.info.assert_called()

        # Find the summary call
        summary_call = None
        for c in mock_logger.info.call_args_list:
            if "Enrichment summary" in str(c):
                summary_call = c
                break

        assert summary_call is not None

    def test_log_enrichment_summary_empty_results(self, runner, mock_logger):
        """Test log_enrichment_summary handles empty results."""
        log_enrichment_summary({}, runner._config.name, mock_logger)

        # Should not log anything for empty results
        summary_calls = [
            c for c in mock_logger.info.call_args_list if "Enrichment summary" in str(c)
        ]
        assert len(summary_calls) == 0
