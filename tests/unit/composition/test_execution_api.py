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
"""Unit tests for execution composition seams."""

from __future__ import annotations

from unittest import mock

import pytest

from bioetl.composition import execution_api

pytestmark = pytest.mark.unit


def test_push_metrics_to_gateway_forwards_restricted_metric_names() -> None:
    with mock.patch(
        "bioetl.composition.observability_runtime.push_metrics_to_gateway",
        return_value=True,
    ) as mock_push:
        result = execution_api.push_metrics_to_gateway(
            run_label="bioetl",
            pipeline_name=None,
            run_type=None,
            grouping_key_extra={"workflow_run_id": "run-123"},
            metric_names=("bioetl_workflow_runs",),
        )

    assert result is True
    mock_push.assert_called_once_with(
        run_label="bioetl",
        pipeline_name=None,
        run_type=None,
        grouping_key_extra={"workflow_run_id": "run-123"},
        metric_names=("bioetl_workflow_runs",),
    )
