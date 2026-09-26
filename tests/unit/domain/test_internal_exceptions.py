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
"""Unit tests for internal domain exceptions."""

from __future__ import annotations

import pytest

from bioetl.domain.exceptions.internal import (
    AuthFailureError,
    CheckpointConflictError,
    LockAcquisitionError,
    LockLostError,
    MergeConflictError,
    MetricsServerError,
    PolicyViolationError,
    RunnerAlreadyExecutedError,
)


@pytest.mark.unit
class TestInvalidStateError:
    """Tests for InvalidStateError exception."""

    def test_imported_correctly(self) -> None:
        """Test that InvalidStateError can be imported."""
        from bioetl.domain.exceptions.internal import InvalidStateError

        assert InvalidStateError is not None

    def test_basic_message(self) -> None:
        """Test InvalidStateError with basic message."""
        from bioetl.domain.exceptions.internal import InvalidStateError

        err = InvalidStateError("Cannot complete run")
        assert "Cannot complete run" in str(err)

    def test_with_state_and_operation(self) -> None:
        """Test InvalidStateError with current_state and attempted_operation."""
        from bioetl.domain.exceptions.internal import InvalidStateError

        err = InvalidStateError(
            "Cannot complete",
            current_state="FAILED",
            attempted_operation="complete",
        )
        assert err.current_state == "FAILED"
        assert err.attempted_operation == "complete"

    def test_without_optional_fields(self) -> None:
        """Test InvalidStateError without optional fields."""
        from bioetl.domain.exceptions.internal import InvalidStateError

        err = InvalidStateError("Error message")
        assert err.current_state is None
        assert err.attempted_operation is None


@pytest.mark.unit
class TestPolicyViolationError:
    """Tests for PolicyViolationError exception."""

    def test_message(self) -> None:
        """Test PolicyViolationError message."""
        err = PolicyViolationError("Bronze layer does not support OVERWRITE mode")
        assert "Bronze layer" in str(err)

    def test_is_critical_error(self) -> None:
        """Test PolicyViolationError inherits from CriticalError."""
        from bioetl.domain.exceptions.base import CriticalError

        err = PolicyViolationError("test")
        assert isinstance(err, CriticalError)

    def test_can_be_raised_and_caught(self) -> None:
        """Test PolicyViolationError can be raised and caught."""
        with pytest.raises(PolicyViolationError, match="OVERWRITE"):
            raise PolicyViolationError("Bronze layer does not support OVERWRITE mode")


@pytest.mark.unit
class TestLockLostError:
    """Tests for LockLostError exception."""

    def test_lock_lost_error__basic_message__8a31ffdd(self) -> None:
        """Test LockLostError with key only."""
        err = LockLostError("lock:chembl_activity")
        assert "lock:chembl_activity" in str(err)
        assert err.key == "lock:chembl_activity"
        assert err.run_id is None

    def test_with_run_id(self) -> None:
        """Test LockLostError with run_id."""
        err = LockLostError("lock:chembl_activity", run_id="run-123")
        assert "run_id=run-123" in str(err)
        assert err.run_id == "run-123"

    def test_without_run_id(self) -> None:
        """Test LockLostError without run_id."""
        err = LockLostError("lock:chembl_activity")
        assert err.run_id is None
        assert "run_id" not in str(err)


@pytest.mark.unit
class TestLockAcquisitionError:
    """Tests for LockAcquisitionError exception."""

    def test_lock_acquisition_error__basic_message__41dd9865(self) -> None:
        """Test LockAcquisitionError with key only."""
        err = LockAcquisitionError("lock:chembl_activity")
        assert "lock:chembl_activity" in str(err)
        assert err.key == "lock:chembl_activity"
        assert err.current_owner is None

    def test_with_current_owner(self) -> None:
        """Test LockAcquisitionError with current_owner."""
        err = LockAcquisitionError("lock:chembl_activity", current_owner="worker-456")
        assert "worker-456" in str(err)
        assert err.current_owner == "worker-456"

    def test_without_current_owner(self) -> None:
        """Test LockAcquisitionError without current_owner."""
        err = LockAcquisitionError("lock:pubchem_compound")
        assert err.current_owner is None
        assert "owned by" not in str(err)


@pytest.mark.unit
class TestCheckpointConflictError:
    """Tests for CheckpointConflictError exception."""

    def test_message_contains_pipeline(self) -> None:
        """Test message includes pipeline name."""
        err = CheckpointConflictError("chembl_activity", "Version mismatch")
        assert "chembl_activity" in str(err)
        assert err.pipeline == "chembl_activity"

    def test_message_contains_conflict_detail(self) -> None:
        """Test message includes conflict detail."""
        err = CheckpointConflictError(
            "pubchem_compound", "Version mismatch: expected 5, found 6"
        )
        assert "Version mismatch" in str(err)


@pytest.mark.unit
class TestMergeConflictError:
    """Tests for MergeConflictError exception."""

    def test_message_contains_table_and_conflicts(self) -> None:
        """Test message includes table and conflict count."""
        err = MergeConflictError("chembl_activity", conflicts=42)
        assert "chembl_activity" in str(err)
        assert "42" in str(err)
        assert err.table == "chembl_activity"
        assert err.conflicts == 42

    def test_zero_conflicts(self) -> None:
        """Test MergeConflictError with zero conflicts."""
        err = MergeConflictError("test_table", conflicts=0)
        assert err.conflicts == 0


@pytest.mark.unit
class TestAuthFailureError:
    """Tests for AuthFailureError exception."""

    def test_auth_failure_error__basic_message__e83763e8(self) -> None:
        """Test AuthFailureError with provider only."""
        err = AuthFailureError("uniprot")
        assert "uniprot" in str(err)
        assert err.provider == "uniprot"
        assert err.status_code is None

    def test_with_status_code(self) -> None:
        """Test AuthFailureError with HTTP status code."""
        err = AuthFailureError("chembl", status_code=401)
        assert "401" in str(err)
        assert err.status_code == 401

    def test_without_status_code(self) -> None:
        """Test AuthFailureError without status code."""
        err = AuthFailureError("pubchem")
        assert "HTTP" not in str(err)
        assert err.status_code is None


@pytest.mark.unit
class TestMetricsServerError:
    """Tests for MetricsServerError exception."""

    def test_metrics_server_error__basic_message__d98e9bbe(self) -> None:
        """Test MetricsServerError with required fields."""
        err = MetricsServerError(port=8000, reason="port_in_use")
        assert "8000" in str(err)
        assert "port_in_use" in str(err)
        assert err.port == 8000
        assert err.reason == "port_in_use"
        assert err.original_error is None

    def test_with_original_error(self) -> None:
        """Test MetricsServerError with underlying exception."""
        original = OSError("Address already in use")
        err = MetricsServerError(port=9090, reason="os_error", original_error=original)
        assert err.original_error is original
        assert err.port == 9090

    def test_without_original_error(self) -> None:
        """Test MetricsServerError without original error."""
        err = MetricsServerError(port=8080, reason="unexpected")
        assert err.original_error is None


@pytest.mark.unit
class TestRunnerAlreadyExecutedError:
    """Tests for RunnerAlreadyExecutedError exception."""

    def test_already_executed_error__basic_message__5bf02b5e(self) -> None:
        """Test RunnerAlreadyExecutedError with required fields."""
        err = RunnerAlreadyExecutedError(
            runner_type="CompositePipelineRunner",
            run_id="run-123",
        )
        assert "CompositePipelineRunner" in str(err)
        assert "run-123" in str(err)
        assert err.runner_type == "CompositePipelineRunner"
        assert err.run_id == "run-123"
        assert err.final_state is None

    def test_with_final_state(self) -> None:
        """Test RunnerAlreadyExecutedError with final_state."""
        err = RunnerAlreadyExecutedError(
            runner_type="CompositePipelineRunner",
            run_id="run-456",
            final_state="COMPLETED",
        )
        assert "COMPLETED" in str(err)
        assert err.final_state == "COMPLETED"

    def test_without_final_state(self) -> None:
        """Test RunnerAlreadyExecutedError without final_state."""
        err = RunnerAlreadyExecutedError(
            runner_type="SinglePipelineRunner",
            run_id="run-789",
        )
        assert err.final_state is None

    def test_message_contains_create_new_instance_hint(self) -> None:
        """Test message hints to create a new instance."""
        err = RunnerAlreadyExecutedError(
            runner_type="PipelineRunner",
            run_id="run-abc",
        )
        assert "new Runner" in str(err) or "Create" in str(err)
