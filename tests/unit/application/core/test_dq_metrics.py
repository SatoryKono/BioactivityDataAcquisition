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
"""Unit tests for DQ mechanisms in Silver."""

from __future__ import annotations

import pytest

from unittest.mock import MagicMock

from bioetl.application.core.batch_metrics import BatchMetricsRecorder
from bioetl.domain.types import ErrorType


pytestmark = pytest.mark.unit


def test_batch_metrics_quarantined_tracking():
    """Test that track_quarantined_records increments the correct metric."""
    mock_metrics = MagicMock()
    recorder = BatchMetricsRecorder(mock_metrics, "pipeline_test", "incremental")

    recorder.track_quarantined_records(ErrorType.DATA_QUALITY, 5)

    mock_metrics.increment_counter.assert_any_call(
        "bioetl_quarantine_records_total",
        5,
        {
            "pipeline": "pipeline_test",
            "reason": "DATA_QUALITY",
        },
    )


def test_batch_metrics_service_noop_when_no_metrics():
    """Test that BatchMetricsRecorderService is a no-op when metrics=None."""
    recorder = BatchMetricsRecorder(None, "pipeline_test", "incremental")

    # Should not raise even with metrics=None
    recorder.track_batch_size("bronze", 10)
    recorder.track_processed_records("silver", 5)
    recorder.track_error("transform", ErrorType.DATA_QUALITY)
    recorder.track_quarantined_records(ErrorType.DATA_QUALITY, 3)
