"""Removal projections count their owning event once across stage interfaces."""

from unittest.mock import Mock

import pytest

from bioetl.application.core.batch_metrics_accounting import _record_processed_stage_accounting, _record_stage_outcome_accounting
from bioetl.domain.run_reports.context import bind_stage_accounting, reset_stage_accounting

pytestmark = pytest.mark.unit


def test_processed_skip_records_silver_removal_reason():
    accounting = Mock()
    token = bind_stage_accounting(accounting)
    try:
        _record_processed_stage_accounting("skipped", 2)
        accounting.record_removal.assert_called_once_with("silver", outcome="skipped", reason_code="OPERATOR_SKIPPED", count=2)
    finally:
        reset_stage_accounting(token)


def test_gold_filter_outcome_does_not_duplicate_per_record_removal():
    accounting = Mock()
    token = bind_stage_accounting(accounting)
    try:
        _record_stage_outcome_accounting("gold", "excluded_by_contract", 2)
        accounting.record_removal.assert_not_called()
    finally:
        reset_stage_accounting(token)
