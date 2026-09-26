"""Stream B APP: leftover current-metrics reconciliation branches."""

from __future__ import annotations

import pytest

from bioetl.application.observability import current_metrics_reconciliation as rec

pytestmark = pytest.mark.unit


def test_reconcile_outcome_empty_gap_and_aligned() -> None:
    empty = rec._reconcile_outcome(
        successes=(),
        workflow_successes=(),
        scrape_has_samples=False,
        scrape_has_workflow=False,
        missing=(),
        missing_workflows=(),
    )
    assert empty.state == "no_durable_success"
    workflow_gap = rec._reconcile_outcome(
        successes=(),
        workflow_successes=("wf",),
        scrape_has_samples=False,
        scrape_has_workflow=False,
        missing=(),
        missing_workflows=("chembl_activity",),
    )
    assert workflow_gap.status == "unhealthy"
    assert (
        rec._gap_state(missing=()) == "durable_workflow_success_without_scrape_samples"
    )
    assert "bioetl_pipeline_runs_total" in rec._gap_message(
        missing=("p",), missing_workflows=()
    )
    assert rec._aligned_message(has_pipelines=True, has_workflows=True)
    assert rec._aligned_message(has_pipelines=False, has_workflows=True)
    assert rec._aligned_message(has_pipelines=True, has_workflows=False)


def test_exposition_sample_helpers_skip_comments() -> None:
    body = (
        "# HELP bioetl_pipeline_runs_total x\n"
        'bioetl_pipeline_runs_total{pipeline="chembl_activity",run_type="incremental"} 1\n'
        'bioetl_workflow_expected{workflow="chembl"} 1\n'
    )
    assert rec._exposition_has_pipeline_runs_sample(body) is True
    assert rec._exposition_has_workflow_expected_sample(body) is True
    assert (
        rec._exposition_has_labeled_pipeline_runs_sample(
            body, pipeline="chembl_activity", run_type="incremental"
        )
        is True
    )
    assert (
        rec._exposition_has_labeled_workflow_expected_sample(body, workflow="chembl")
        is True
    )
    assert rec._exposition_has_pipeline_runs_sample("# only comment") is False
