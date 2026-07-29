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
"""Unit tests for runner_constants — shared exception groups for CompositePipelineRunner."""

from __future__ import annotations

import pytest

from bioetl.application.composite.runner_pkg.runner_constants import (
    CHECKPOINT_NON_FATAL_ERRORS,
    DQ_REPORT_NON_FATAL_ERRORS,
    PIPELINE_EXECUTION_ERRORS,
    QUARANTINE_WRITE_NON_FATAL_ERRORS,
)
from bioetl.domain.exceptions import (
    CheckpointConflictError,
    DataQualityError,
    NetworkError,
    StorageError,
)


# ---------------------------------------------------------------------------
# CHECKPOINT_NON_FATAL_ERRORS
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_checkpoint_non_fatal_errors_is_tuple() -> None:
    assert isinstance(CHECKPOINT_NON_FATAL_ERRORS, tuple)


@pytest.mark.unit
@pytest.mark.parametrize(
    "exc_type",
    [
        CheckpointConflictError,
        StorageError,
        OSError,
        ValueError,
        TypeError,
    ],
)
def test_checkpoint_non_fatal_errors_contains_expected_types(
    exc_type: type[BaseException],
) -> None:
    assert exc_type in CHECKPOINT_NON_FATAL_ERRORS


@pytest.mark.unit
def test_checkpoint_non_fatal_errors_catches_instances() -> None:
    """Verify the tuple is usable in an except clause for each member.

    CheckpointConflictError requires (pipeline, message) — other built-in
    exceptions accept a single string argument.
    """
    for exc_type in CHECKPOINT_NON_FATAL_ERRORS:
        if exc_type is CheckpointConflictError:
            instance: BaseException = exc_type("test_pipeline", "conflict")
        else:
            instance = exc_type("boom")
        try:
            raise instance
        except CHECKPOINT_NON_FATAL_ERRORS:
            pass  # expected
        else:
            pytest.fail(f"{exc_type} was not caught by CHECKPOINT_NON_FATAL_ERRORS")


# ---------------------------------------------------------------------------
# PIPELINE_EXECUTION_ERRORS
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_pipeline_execution_errors_is_tuple() -> None:
    assert isinstance(PIPELINE_EXECUTION_ERRORS, tuple)


@pytest.mark.unit
@pytest.mark.parametrize(
    "exc_type",
    [
        NetworkError,
        StorageError,
        CheckpointConflictError,
        DataQualityError,
        RuntimeError,
        ValueError,
        TypeError,
        OSError,
    ],
)
def test_pipeline_execution_errors_contains_expected_types(
    exc_type: type[BaseException],
) -> None:
    assert exc_type in PIPELINE_EXECUTION_ERRORS


@pytest.mark.unit
def test_pipeline_execution_errors_does_not_catch_unrelated_exception() -> None:
    """KeyError is not in PIPELINE_EXECUTION_ERRORS and should propagate."""
    with pytest.raises(KeyError):
        try:
            raise KeyError("unexpected")
        except PIPELINE_EXECUTION_ERRORS:
            pytest.fail("KeyError should not be caught")


# ---------------------------------------------------------------------------
# DQ_REPORT_NON_FATAL_ERRORS
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_dq_report_non_fatal_errors_is_tuple() -> None:
    assert isinstance(DQ_REPORT_NON_FATAL_ERRORS, tuple)


@pytest.mark.unit
@pytest.mark.parametrize(
    "exc_type",
    [
        DataQualityError,
        StorageError,
        ImportError,
        ModuleNotFoundError,
        RuntimeError,
        ValueError,
        TypeError,
        OSError,
    ],
)
def test_dq_report_non_fatal_errors_contains_expected_types(
    exc_type: type[BaseException],
) -> None:
    assert exc_type in DQ_REPORT_NON_FATAL_ERRORS


# ---------------------------------------------------------------------------
# QUARANTINE_WRITE_NON_FATAL_ERRORS
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_quarantine_write_non_fatal_errors_is_tuple() -> None:
    assert isinstance(QUARANTINE_WRITE_NON_FATAL_ERRORS, tuple)


@pytest.mark.unit
@pytest.mark.parametrize(
    "exc_type",
    [
        StorageError,
        DataQualityError,
        OSError,
        ValueError,
        TypeError,
    ],
)
def test_quarantine_write_non_fatal_errors_contains_expected_types(
    exc_type: type[BaseException],
) -> None:
    assert exc_type in QUARANTINE_WRITE_NON_FATAL_ERRORS


@pytest.mark.unit
def test_all_exported_names_are_tuples() -> None:
    """All exported constants must be tuples (usable in except clauses)."""
    for name, value in [
        ("CHECKPOINT_NON_FATAL_ERRORS", CHECKPOINT_NON_FATAL_ERRORS),
        ("DQ_REPORT_NON_FATAL_ERRORS", DQ_REPORT_NON_FATAL_ERRORS),
        ("PIPELINE_EXECUTION_ERRORS", PIPELINE_EXECUTION_ERRORS),
        ("QUARANTINE_WRITE_NON_FATAL_ERRORS", QUARANTINE_WRITE_NON_FATAL_ERRORS),
    ]:
        assert isinstance(value, tuple), f"{name} must be a tuple"
        assert len(value) > 0, f"{name} must not be empty"
