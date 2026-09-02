"""Regression tests for allowlisted Grafana action-target routes."""

from __future__ import annotations

from scripts.ops.observability.grafana.action_target_routes import (
    ACTION_DASHBOARD_UID_BY_TARGET,
    DQ_REASON_RULES_RUNBOOK,
    dashboard_uid_for_target,
    row_aware_dashboard_url,
)


def test_dashboard_uid_for_target_is_allowlisted_and_fail_closed() -> None:
    assert dashboard_uid_for_target("runtime") == "bioetl-runtime"
    assert dashboard_uid_for_target("data_quality") == "bioetl-dq-v2"
    assert dashboard_uid_for_target("verify_dq_reason_rules") is None
    assert dashboard_uid_for_target("future_target") is None


def test_row_aware_dashboard_url_uses_the_row_uid_and_scope_variables() -> None:
    url = row_aware_dashboard_url()

    assert "/d/${__data.fields.action_dashboard_uid}/" in url
    assert "var-workflow=$workflow" in url
    assert "var-pipeline=$pipeline" in url
    assert "var-run_type=$run_type" in url
    assert "var-run_id=$run_id" in url


def test_exported_target_map_and_runbook_are_explicit() -> None:
    assert ACTION_DASHBOARD_UID_BY_TARGET["provider"] == "bioetl-provider-health-v2"
    assert ACTION_DASHBOARD_UID_BY_TARGET["dq"] == "bioetl-dq-v2"
    assert DQ_REASON_RULES_RUNBOOK.endswith(
        "docs/05-operations/runbooks/observability-checklist.md"
    )
