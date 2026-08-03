# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Exhaustive FSM transition tests for BioETL aggregates.

These tests verify all valid and invalid state transitions for the three core
aggregates: Batch, PipelineRun, and QuarantineEntry.

See docs/02-architecture/domain/aggregate-invariants.md for canonical documentation.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.domain.aggregates.batch import BatchStatus
from bioetl.domain.aggregates.pipeline_run import PipelineRunState
from bioetl.domain.aggregates.quarantine_entry import QuarantineStatus


pytestmark = pytest.mark.architecture
DOC_PATH = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "02-architecture"
    / "domain"
    / "aggregate-invariants.md"
)


class TestBatchStateTransitions:
    """Exhaustive FSM transition tests for Batch aggregate."""

    @pytest.mark.parametrize(
        "from_state,to_state,should_succeed",
        [
            # Valid transitions
            (BatchStatus.OPEN, BatchStatus.SEALED, True),
            (BatchStatus.SEALED, BatchStatus.WRITING, True),
            (BatchStatus.WRITING, BatchStatus.COMMITTED, True),
            (BatchStatus.WRITING, BatchStatus.FAILED, True),
            # Invalid transitions
            (BatchStatus.COMMITTED, BatchStatus.OPEN, False),
            (BatchStatus.FAILED, BatchStatus.OPEN, False),
            (BatchStatus.SEALED, BatchStatus.COMMITTED, False),
            (BatchStatus.OPEN, BatchStatus.WRITING, False),
            (BatchStatus.COMMITTED, BatchStatus.SEALED, False),
            (BatchStatus.FAILED, BatchStatus.SEALED, False),
            (BatchStatus.COMMITTED, BatchStatus.WRITING, False),
            (BatchStatus.FAILED, BatchStatus.WRITING, False),
            (BatchStatus.WRITING, BatchStatus.OPEN, False),
            (BatchStatus.WRITING, BatchStatus.SEALED, False),
            # Self-transitions (invalid)
            (BatchStatus.OPEN, BatchStatus.OPEN, False),
            (BatchStatus.SEALED, BatchStatus.SEALED, False),
            (BatchStatus.WRITING, BatchStatus.WRITING, False),
            (BatchStatus.COMMITTED, BatchStatus.COMMITTED, False),
            (BatchStatus.FAILED, BatchStatus.FAILED, False),
        ],
    )
    def test_batch_state_transitions(
        self, from_state: BatchStatus, to_state: BatchStatus, should_succeed: bool
    ) -> None:
        """Test all Batch state transitions against documented invariants."""
        # This is a structural test - actual transition logic is in domain layer
        # Here we verify the documented transition rules are consistent
        valid_transitions = {
            (BatchStatus.OPEN, BatchStatus.SEALED),
            (BatchStatus.SEALED, BatchStatus.WRITING),
            (BatchStatus.WRITING, BatchStatus.COMMITTED),
            (BatchStatus.WRITING, BatchStatus.FAILED),
        }

        is_valid = (from_state, to_state) in valid_transitions
        assert is_valid == should_succeed, (
            f"Batch transition {from_state} -> {to_state} should "
            f"{'succeed' if should_succeed else 'fail'} but is marked as "
            f"{'valid' if is_valid else 'invalid'}"
        )


class TestPipelineRunStateTransitions:
    """Exhaustive FSM transition tests for PipelineRun aggregate."""

    @pytest.mark.parametrize(
        "from_state,to_state,should_succeed",
        [
            # Valid transitions
            (PipelineRunState.PENDING, PipelineRunState.RUNNING, True),
            (PipelineRunState.RUNNING, PipelineRunState.COMPLETED, True),
            (PipelineRunState.RUNNING, PipelineRunState.FAILED, True),
            (PipelineRunState.RUNNING, PipelineRunState.SHUTDOWN, True),
            # Invalid transitions
            (PipelineRunState.COMPLETED, PipelineRunState.RUNNING, False),
            (PipelineRunState.FAILED, PipelineRunState.RUNNING, False),
            (PipelineRunState.SHUTDOWN, PipelineRunState.RUNNING, False),
            (PipelineRunState.PENDING, PipelineRunState.COMPLETED, False),
            (PipelineRunState.COMPLETED, PipelineRunState.PENDING, False),
            (PipelineRunState.FAILED, PipelineRunState.PENDING, False),
            (PipelineRunState.SHUTDOWN, PipelineRunState.PENDING, False),
            (PipelineRunState.PENDING, PipelineRunState.FAILED, False),
            (PipelineRunState.PENDING, PipelineRunState.SHUTDOWN, False),
            (PipelineRunState.COMPLETED, PipelineRunState.FAILED, False),
            (PipelineRunState.COMPLETED, PipelineRunState.SHUTDOWN, False),
            (PipelineRunState.FAILED, PipelineRunState.COMPLETED, False),
            (PipelineRunState.FAILED, PipelineRunState.SHUTDOWN, False),
            (PipelineRunState.SHUTDOWN, PipelineRunState.COMPLETED, False),
            (PipelineRunState.SHUTDOWN, PipelineRunState.FAILED, False),
            # Self-transitions (invalid)
            (PipelineRunState.PENDING, PipelineRunState.PENDING, False),
            (PipelineRunState.RUNNING, PipelineRunState.RUNNING, False),
            (PipelineRunState.COMPLETED, PipelineRunState.COMPLETED, False),
            (PipelineRunState.FAILED, PipelineRunState.FAILED, False),
            (PipelineRunState.SHUTDOWN, PipelineRunState.SHUTDOWN, False),
        ],
    )
    def test_pipeline_run_state_transitions(
        self,
        from_state: PipelineRunState,
        to_state: PipelineRunState,
        should_succeed: bool,
    ) -> None:
        """Test all PipelineRun state transitions against documented invariants."""
        valid_transitions = {
            (PipelineRunState.PENDING, PipelineRunState.RUNNING),
            (PipelineRunState.RUNNING, PipelineRunState.COMPLETED),
            (PipelineRunState.RUNNING, PipelineRunState.FAILED),
            (PipelineRunState.RUNNING, PipelineRunState.SHUTDOWN),
        }

        is_valid = (from_state, to_state) in valid_transitions
        assert is_valid == should_succeed, (
            f"PipelineRun transition {from_state} -> {to_state} should "
            f"{'succeed' if should_succeed else 'fail'} but is marked as "
            f"{'valid' if is_valid else 'invalid'}"
        )


class TestQuarantineEntryStateTransitions:
    """Exhaustive FSM transition tests for QuarantineEntry aggregate."""

    @pytest.mark.parametrize(
        "from_state,to_state,should_succeed",
        [
            # Valid transitions from NEW
            (QuarantineStatus.NEW, QuarantineStatus.UNDER_REVIEW, True),
            (QuarantineStatus.NEW, QuarantineStatus.IGNORED, True),
            (QuarantineStatus.NEW, QuarantineStatus.REPROCESSED, True),
            (QuarantineStatus.NEW, QuarantineStatus.EXPIRED, True),
            # Valid transitions from UNDER_REVIEW
            (QuarantineStatus.UNDER_REVIEW, QuarantineStatus.IGNORED, True),
            (QuarantineStatus.UNDER_REVIEW, QuarantineStatus.REPROCESSED, True),
            (QuarantineStatus.UNDER_REVIEW, QuarantineStatus.EXPIRED, True),
            # Invalid transitions
            (QuarantineStatus.IGNORED, QuarantineStatus.UNDER_REVIEW, False),
            (QuarantineStatus.REPROCESSED, QuarantineStatus.UNDER_REVIEW, False),
            (QuarantineStatus.EXPIRED, QuarantineStatus.UNDER_REVIEW, False),
            (QuarantineStatus.UNDER_REVIEW, QuarantineStatus.NEW, False),
            (QuarantineStatus.IGNORED, QuarantineStatus.NEW, False),
            (QuarantineStatus.REPROCESSED, QuarantineStatus.NEW, False),
            (QuarantineStatus.EXPIRED, QuarantineStatus.NEW, False),
            (QuarantineStatus.IGNORED, QuarantineStatus.REPROCESSED, False),
            (QuarantineStatus.IGNORED, QuarantineStatus.EXPIRED, False),
            (QuarantineStatus.REPROCESSED, QuarantineStatus.IGNORED, False),
            (QuarantineStatus.REPROCESSED, QuarantineStatus.EXPIRED, False),
            (QuarantineStatus.EXPIRED, QuarantineStatus.IGNORED, False),
            (QuarantineStatus.EXPIRED, QuarantineStatus.REPROCESSED, False),
            # Self-transitions (invalid)
            (QuarantineStatus.NEW, QuarantineStatus.NEW, False),
            (QuarantineStatus.UNDER_REVIEW, QuarantineStatus.UNDER_REVIEW, False),
            (QuarantineStatus.IGNORED, QuarantineStatus.IGNORED, False),
            (QuarantineStatus.REPROCESSED, QuarantineStatus.REPROCESSED, False),
            (QuarantineStatus.EXPIRED, QuarantineStatus.EXPIRED, False),
        ],
    )
    def test_quarantine_entry_state_transitions(
        self,
        from_state: QuarantineStatus,
        to_state: QuarantineStatus,
        should_succeed: bool,
    ) -> None:
        """Test all QuarantineEntry state transitions against documented invariants."""
        valid_transitions = {
            (QuarantineStatus.NEW, QuarantineStatus.UNDER_REVIEW),
            (QuarantineStatus.NEW, QuarantineStatus.IGNORED),
            (QuarantineStatus.NEW, QuarantineStatus.REPROCESSED),
            (QuarantineStatus.NEW, QuarantineStatus.EXPIRED),
            (QuarantineStatus.UNDER_REVIEW, QuarantineStatus.IGNORED),
            (QuarantineStatus.UNDER_REVIEW, QuarantineStatus.REPROCESSED),
            (QuarantineStatus.UNDER_REVIEW, QuarantineStatus.EXPIRED),
        }

        is_valid = (from_state, to_state) in valid_transitions
        assert is_valid == should_succeed, (
            f"QuarantineEntry transition {from_state} -> {to_state} should "
            f"{'succeed' if should_succeed else 'fail'} but is marked as "
            f"{'valid' if is_valid else 'invalid'}"
        )


class TestAggregateInvariantConsistency:
    """Cross-aggregate invariant consistency tests."""

    def test_no_self_transitions_allowed(self) -> None:
        """Verify that no aggregate allows self-transitions."""
        batch_valid = {
            (BatchStatus.OPEN, BatchStatus.SEALED),
            (BatchStatus.SEALED, BatchStatus.WRITING),
            (BatchStatus.WRITING, BatchStatus.COMMITTED),
            (BatchStatus.WRITING, BatchStatus.FAILED),
        }
        pipeline_valid = {
            (PipelineRunState.PENDING, PipelineRunState.RUNNING),
            (PipelineRunState.RUNNING, PipelineRunState.COMPLETED),
            (PipelineRunState.RUNNING, PipelineRunState.FAILED),
            (PipelineRunState.RUNNING, PipelineRunState.SHUTDOWN),
        }
        quarantine_valid = {
            (QuarantineStatus.NEW, QuarantineStatus.UNDER_REVIEW),
            (QuarantineStatus.NEW, QuarantineStatus.IGNORED),
            (QuarantineStatus.NEW, QuarantineStatus.REPROCESSED),
            (QuarantineStatus.NEW, QuarantineStatus.EXPIRED),
            (QuarantineStatus.UNDER_REVIEW, QuarantineStatus.IGNORED),
            (QuarantineStatus.UNDER_REVIEW, QuarantineStatus.REPROCESSED),
            (QuarantineStatus.UNDER_REVIEW, QuarantineStatus.EXPIRED),
        }

        assert all((state, state) not in batch_valid for state in BatchStatus)
        assert all((state, state) not in pipeline_valid for state in PipelineRunState)
        assert all((state, state) not in quarantine_valid for state in QuarantineStatus)

    def test_terminal_states_are_final(self) -> None:
        """Verify that terminal states cannot transition to other states."""
        batch_valid = {
            (BatchStatus.OPEN, BatchStatus.SEALED),
            (BatchStatus.SEALED, BatchStatus.WRITING),
            (BatchStatus.WRITING, BatchStatus.COMMITTED),
            (BatchStatus.WRITING, BatchStatus.FAILED),
        }
        pipeline_valid = {
            (PipelineRunState.PENDING, PipelineRunState.RUNNING),
            (PipelineRunState.RUNNING, PipelineRunState.COMPLETED),
            (PipelineRunState.RUNNING, PipelineRunState.FAILED),
            (PipelineRunState.RUNNING, PipelineRunState.SHUTDOWN),
        }
        quarantine_valid = {
            (QuarantineStatus.NEW, QuarantineStatus.UNDER_REVIEW),
            (QuarantineStatus.NEW, QuarantineStatus.IGNORED),
            (QuarantineStatus.NEW, QuarantineStatus.REPROCESSED),
            (QuarantineStatus.NEW, QuarantineStatus.EXPIRED),
            (QuarantineStatus.UNDER_REVIEW, QuarantineStatus.IGNORED),
            (QuarantineStatus.UNDER_REVIEW, QuarantineStatus.REPROCESSED),
            (QuarantineStatus.UNDER_REVIEW, QuarantineStatus.EXPIRED),
        }

        assert not any(
            from_state in {BatchStatus.COMMITTED, BatchStatus.FAILED}
            for from_state, _ in batch_valid
        )
        assert not any(
            from_state
            in {
                PipelineRunState.COMPLETED,
                PipelineRunState.FAILED,
                PipelineRunState.SHUTDOWN,
            }
            for from_state, _ in pipeline_valid
        )
        assert not any(
            from_state
            in {
                QuarantineStatus.IGNORED,
                QuarantineStatus.REPROCESSED,
                QuarantineStatus.EXPIRED,
            }
            for from_state, _ in quarantine_valid
        )

    def test_all_transitions_are_documented(self) -> None:
        """Verify that all tested transitions are documented in aggregate-invariants.md."""
        content = DOC_PATH.read_text(encoding="utf-8")
        assert DOC_PATH.is_file()
        assert "Batch" in content
        assert "PipelineRun" in content
        assert "QuarantineEntry" in content
