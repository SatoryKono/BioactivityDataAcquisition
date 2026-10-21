"""Incomplete DQ facts and secondary report failures retain their meaning."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bioetl.application.core._quarantine_metrics_support import (
    filtered_reason_code_from_details,
)
from bioetl.application.core.batch_transformer_attempt_success import (
    _primary_dq_affected_field,
)
from bioetl.application.services.dq.gold_filter_diagnostics import (
    gold_exclusion_reason_code,
)
from bioetl.application.services.execution._pipeline_runner_support import (
    finalize_terminal_evidence,
)
from bioetl.application.services.execution.pipeline_run_execution_service import (
    format_run_error_message,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("details", [{}, {"reason_code": "  "}, {"reason_code": 1}])
def test_unusable_filter_reason_keeps_explicit_fallback(details):
    assert (
        filtered_reason_code_from_details(details, fallback="FILTERED_OUT")
        == "FILTERED_OUT"
    )


def test_nonblocking_or_unbound_dq_outcome_never_invents_a_field():
    outcomes = [
        SimpleNamespace(disposition="warn", affected_fields=("id",)),
        SimpleNamespace(
            disposition="reject", affected_fields=(), rule_id="global-rule"
        ),
    ]
    assert _primary_dq_affected_field(outcomes, "reject") is None


def test_gold_rejection_requires_reason_but_not_a_field():
    with pytest.raises(ValueError, match="missing reason_code"):
        gold_exclusion_reason_code({"field": "id"})
    assert gold_exclusion_reason_code({"reason_code": " INELIGIBLE "}) == "INELIGIBLE"


def test_secondary_report_failure_preserves_primary_execution_error():
    report_error = OSError("disk full")
    logger = Mock()
    write_report = Mock(side_effect=report_error)
    finalize_terminal_evidence(
        write_report,
        execution_error=RuntimeError("primary"),
        logger=logger,
        event="report_failed",
    )
    write_report.assert_called_once_with()
    logger.error.assert_called_once_with("report_failed", error="disk full")


def test_report_failure_without_primary_error_propagates_original_exception():
    error = OSError("disk full")
    logger = Mock()
    with pytest.raises(OSError) as caught:
        finalize_terminal_evidence(
            Mock(side_effect=error),
            execution_error=None,
            logger=logger,
            event="report_failed",
        )
    assert caught.value is error
    logger.error.assert_not_called()


def test_successful_report_is_written_once():
    report = Mock()
    finalize_terminal_evidence(
        report, execution_error=None, logger=Mock(), event="report_failed"
    )
    report.assert_called_once_with()


def test_exception_with_blank_text_retains_type_and_arguments():
    class BlankError(ValueError):
        def __str__(self):
            return " "

    assert (
        format_run_error_message(BlankError("identity missing"))
        == "BlankError: ('identity missing',)"
    )


def test_quarantine_error_counts_preserve_each_original_classification():
    from bioetl.application.core._quarantine_metrics_support import count_dq_error_types
    from bioetl.domain.types import ErrorType

    records = [
        ({}, ErrorType.INVALID_DATA, "first"),
        ({}, ErrorType.INVALID_DATA, "second"),
        ({}, ErrorType.DB_UNAVAILABLE, "storage"),
    ]
    assert count_dq_error_types(records) == {
        ErrorType.INVALID_DATA: 2,
        ErrorType.DB_UNAVAILABLE: 1,
    }
    assert count_dq_error_types([]) == {}


def test_field_validation_error_retains_its_normalized_field_reason():
    from bioetl.application.core.batch_transformer_attempt_failures import (
        _resolve_quarantine_reason_code,
    )
    from bioetl.domain.types import ErrorType

    class FieldError(ValueError):
        field = " units "

    assert (
        _resolve_quarantine_reason_code(
            FieldError("invalid units"), error_type=ErrorType.INVALID_DATA
        )
        == f"{ErrorType.INVALID_DATA.value}:units"
    )


@pytest.mark.parametrize("details", [None, [], "reason"])
def test_nonmapping_filter_details_use_the_explicit_fallback(details):
    from bioetl.application.core._quarantine_metrics_support import (
        filtered_reason_code_from_details,
    )

    assert filtered_reason_code_from_details(details, fallback="filtered") == "filtered"
