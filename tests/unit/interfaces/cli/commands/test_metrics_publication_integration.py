"""Unit tests for CLI metrics publication helpers."""

from __future__ import annotations

from unittest.mock import patch

from bioetl.interfaces.cli.commands.domains.health.metrics_publication_integration import (
    publish_metrics_safely,
)


def test_publish_metrics_safely_delegates_to_execution_api() -> None:
    with patch(
        "bioetl.composition.execution_api.push_metrics_to_gateway",
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
        "bioetl.composition.execution_api.push_metrics_to_gateway",
        side_effect=RuntimeError("push failed"),
    ):
        result = publish_metrics_safely(
            run_label="bioetl",
            pipeline_name="workflow_chembl_activity",
        )

    assert result is False
