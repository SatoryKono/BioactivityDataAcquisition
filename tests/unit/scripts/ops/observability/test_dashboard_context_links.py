"""Unit tests for canonical Grafana dashboard context URLs."""

from __future__ import annotations

import pytest

from scripts.ops.observability.grafana.dashboard_context_links import (
    DashboardContext,
    RunIdError,
    build_handoff_url,
    normalize_run_id,
    preserves_time_window,
    rewrite_dashboard_handoff_url,
    urls_for_context,
)

from scripts.ops.observability.grafana.action_target_routes import (
    ACTION_DASHBOARD_UID_BY_TARGET,
    dashboard_uid_for_target,
    row_aware_dashboard_url,
)

pytestmark = pytest.mark.unit


def test_normalize_run_id_trims_and_rejects_internal_space() -> None:
    assert normalize_run_id("  abc-def  ") == "abc-def"
    with pytest.raises(RunIdError):
        normalize_run_id("  ")
    with pytest.raises(RunIdError):
        normalize_run_id("ab cd")


def test_rewrite_fills_missing_run_id_and_time() -> None:
    url = rewrite_dashboard_handoff_url(
        "/d/bioetl-run-explorer-v1/bioetl-run-explorer-v1?var-pipeline=$pipeline"
    )
    assert "var-run_id=$run_id" in url
    assert preserves_time_window(url)
    viewpanel = rewrite_dashboard_handoff_url(
        "/d/bioetl-runtime/bioetl-runtime?viewPanel=9401&var-pipeline=$pipeline"
        "&var-run_type=$run_type&var-stage=$stage&${__url_time_range}"
    )
    assert "var-run_id=" not in viewpanel
    assert preserves_time_window(viewpanel)


def test_rewrite_trims_concrete_run_id() -> None:
    url = rewrite_dashboard_handoff_url(
        "/d/bioetl-control-plane-v1/bioetl-control-plane-v1"
        "?var-run_id=%20%2068c11d41-1d2f-5dc9-b041-9265bc485046"
    )
    assert "var-run_id=68c11d41-1d2f-5dc9-b041-9265bc485046" in url


def test_template_handoff_uses_pipeline_context_from_provider_board() -> None:
    url = build_handoff_url(
        "bioetl-overview-v2",
        source_uid="bioetl-provider-health-v2",
        template=True,
    )
    assert "var-pipeline=$pipeline_context" in url
    assert "var-run_id=$run_id" in url


def test_urls_for_context_do_not_keep_a_foreign_uuid() -> None:
    context = DashboardContext(
        workflow="wf",
        pipeline="chembl_assay",
        run_type="backfill",
        run_id="68c11d41-1d2f-5dc9-b041-9265bc485046",
    )
    urls = urls_for_context(context)
    assert "64927" not in "".join(urls.values())
    assert all(
        "var-run_id=68c11d41-1d2f-5dc9-b041-9265bc485046" in url
        for url in urls.values()
    )


def test_action_targets_use_allowlisted_dashboard_routes() -> None:
    assert dashboard_uid_for_target("runtime") == "bioetl-runtime"
    assert dashboard_uid_for_target("data_quality") == "bioetl-dq-v2"
    assert dashboard_uid_for_target("verify_dq_reason_rules") is None
    assert dashboard_uid_for_target("unknown") is None
    assert ACTION_DASHBOARD_UID_BY_TARGET["provider"] == "bioetl-provider-health-v2"

    url = row_aware_dashboard_url()
    assert "${__data.fields.action_dashboard_uid}" in url
    assert "var-run_id=$run_id" in url
    assert "${__url_time_range}" in url
