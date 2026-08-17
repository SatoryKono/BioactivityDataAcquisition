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
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for the Pure FSM governing BatchExecutor."""

from __future__ import annotations

import pytest

from bioetl.application.core.lifecycle.batch_fsm import (
    BatchExecutionCommand,
    BatchExecutionEvent,
    BatchExecutionFSM,
    BatchExecutionState,
    IllegalStateTransitionError,
)


@pytest.fixture
def fsm() -> BatchExecutionFSM:
    return BatchExecutionFSM()


@pytest.mark.unit
class TestBatchExecutionFSM:
    def test_normal_happy_path(self, fsm: BatchExecutionFSM) -> None:
        """Tests the full happy path loop of a single batch."""
        # 1. Start
        r1 = fsm.advance(BatchExecutionState.IDLE, BatchExecutionEvent.RUN_STARTED)
        assert r1.new_state == BatchExecutionState.STREAMING

        # 2. Batch Assembled -> Processing
        r2 = fsm.advance(r1.new_state, BatchExecutionEvent.BATCH_ASSEMBLED)
        assert r2.new_state == BatchExecutionState.PROCESSING
        assert BatchExecutionCommand.PROCESS_BATCH in r2.commands

        # 3. Processing -> State Commit
        r3 = fsm.advance(r2.new_state, BatchExecutionEvent.PROCESS_SUCCEEDED)
        assert r3.new_state == BatchExecutionState.STATE_COMMIT
        assert BatchExecutionCommand.COMMIT_STATE in r3.commands

        # 4. State Commit -> Checkpoint Evaluation
        r4 = fsm.advance(r3.new_state, BatchExecutionEvent.STATE_COMMITTED)
        assert r4.new_state == BatchExecutionState.CHECKPOINT_EVALUATION

        # 5. Checkpoint Not Required -> Back to Streaming
        r5 = fsm.advance(r4.new_state, BatchExecutionEvent.CHECKPOINT_NOT_REQUIRED)
        assert r5.new_state == BatchExecutionState.STREAMING

    def test_checkpoint_saving_path(self, fsm: BatchExecutionFSM) -> None:
        """Tests the transition through required checkpoint saving."""
        state = BatchExecutionState.CHECKPOINT_EVALUATION

        # Requires checkpoint
        r1 = fsm.advance(state, BatchExecutionEvent.CHECKPOINT_REQUIRED)
        assert r1.new_state == BatchExecutionState.CHECKPOINT_EVALUATION
        assert BatchExecutionCommand.SAVE_CHECKPOINT in r1.commands

        # Saved
        r2 = fsm.advance(r1.new_state, BatchExecutionEvent.CHECKPOINT_SAVED)
        assert r2.new_state == BatchExecutionState.STREAMING

    def test_shutdown_path(self, fsm: BatchExecutionFSM) -> None:
        """Tests graceful shutdown requested during streaming."""
        r1 = fsm.advance(
            BatchExecutionState.STREAMING, BatchExecutionEvent.SHUTDOWN_REQUESTED
        )
        assert r1.new_state == BatchExecutionState.SHUTTING_DOWN
        assert BatchExecutionCommand.SAVE_CHECKPOINT in r1.commands
        assert BatchExecutionCommand.STOP_LOOP in r1.commands

        r2 = fsm.advance(r1.new_state, BatchExecutionEvent.CHECKPOINT_SAVED)
        assert r2.new_state == BatchExecutionState.DONE

    def test_shutdown_checkpoint_failed_transitions_to_failed(
        self, fsm: BatchExecutionFSM
    ) -> None:
        """SHUTTING_DOWN + CHECKPOINT_FAILED must fail closed like evaluation."""
        result = fsm.advance(
            BatchExecutionState.SHUTTING_DOWN,
            BatchExecutionEvent.CHECKPOINT_FAILED,
        )
        assert result.new_state == BatchExecutionState.FAILED
        assert BatchExecutionCommand.PROPAGATE_ERROR in result.commands

    def test_failure_transitions(self, fsm: BatchExecutionFSM) -> None:
        """Tests that failures in critical stages propagate to FAILED state."""
        stages = [
            (BatchExecutionState.PROCESSING, BatchExecutionEvent.PROCESS_FAILED),
            (BatchExecutionState.STATE_COMMIT, BatchExecutionEvent.STATE_COMMIT_FAILED),
            (
                BatchExecutionState.CHECKPOINT_EVALUATION,
                BatchExecutionEvent.CHECKPOINT_FAILED,
            ),
        ]

        for current_state, event in stages:
            res = fsm.advance(current_state, event)
            assert res.new_state == BatchExecutionState.FAILED
            assert BatchExecutionCommand.PROPAGATE_ERROR in res.commands

    def test_illegal_transition_raises_error(self, fsm: BatchExecutionFSM) -> None:
        """Tests that nonsensical transitions raise IllegalStateTransitionError."""
        invalid_pairs = [
            (BatchExecutionState.IDLE, BatchExecutionEvent.PROCESS_SUCCEEDED),
            (BatchExecutionState.PROCESSING, BatchExecutionEvent.BATCH_ASSEMBLED),
            (BatchExecutionState.STATE_COMMIT, BatchExecutionEvent.SHUTDOWN_REQUESTED),
        ]

        for current_state, event in invalid_pairs:
            with pytest.raises(IllegalStateTransitionError):
                fsm.advance(current_state, event)
