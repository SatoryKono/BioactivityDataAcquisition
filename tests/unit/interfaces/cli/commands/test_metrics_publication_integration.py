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
"""Unit tests for CLI metrics publication helpers."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from bioetl.interfaces.cli.commands.domains.health.metrics_publication_integration import (
    publish_metrics_safely,
)

pytestmark = pytest.mark.unit


def test_publish_metrics_safely_delegates_to_observability_api() -> None:
    with patch(
        "bioetl.composition.observability_api.push_metrics_to_gateway",
        return_value=True,
    ) as mock_push:
        result = publish_metrics_safely(
            run_label="bioetl",
            pipeline_name="workflow_chembl_activity",
            run_type="backfill",
            grouping_key_extra={"workflow_run_id": "run-123"},
            metric_names=("bioetl_workflow_runs",),
        )

    assert result is True
    mock_push.assert_called_once_with(
        run_label="bioetl",
        pipeline_name="workflow_chembl_activity",
        run_type="backfill",
        grouping_key_extra={"workflow_run_id": "run-123"},
        metric_names=("bioetl_workflow_runs",),
    )


def test_publish_metrics_safely_swallows_observability_failures() -> None:
    with patch(
        "bioetl.composition.observability_api.push_metrics_to_gateway",
        side_effect=RuntimeError("push failed"),
    ):
        result = publish_metrics_safely(
            run_label="bioetl",
            pipeline_name="workflow_chembl_activity",
        )

    assert result is False


def test_publish_metrics_safely_propagates_failed_publication_result() -> None:
    with patch(
        "bioetl.composition.observability_api.push_metrics_to_gateway",
        return_value=False,
    ):
        result = publish_metrics_safely(
            run_label="bioetl",
            pipeline_name="chembl_activity",
            run_type="incremental",
        )

    assert result is False
