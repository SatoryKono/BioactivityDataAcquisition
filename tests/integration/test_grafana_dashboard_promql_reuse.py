"""Grafana dashboard PromQL reuse contracts."""

from pathlib import Path

import pytest

from tests.integration._grafana_test_support import (
    get_dashboard_files,
    get_dashboard_panels,
    load_dashboard,
)


pytestmark = pytest.mark.integration


def _expected_duplicate_uses() -> dict[str, set[tuple[str, str]]]:
    return {
        '((sum((bioetl_dq_validation_score{pipeline=~"$pipeline"} * '
        'bioetl_dq_validation_record_count{pipeline=~"$pipeline"}))) / '
        'clamp_min(sum(bioetl_dq_validation_record_count{pipeline=~"$pipeline"}), '
        "1))": {
            (
                "bioetl-dq-v2.json",
                "Monitor: Data Quality Score (Volume-weighted)",
            ),
            (
                "bioetl-dq-v2.json",
                "Track: Data Quality Score Trend (Volume-weighted)",
            ),
        },
        'max(bioetl_dq_current_status{pipeline=~"$pipeline"})': {
            ("bioetl-dq-v2.json", "Monitor DQ Current Status"),
            ("bioetl-dq-v2.json", "Status"),
        },
        'max(bioetl_runtime_current_status_trusted{pipeline=~"$pipeline",run_type=~"$run_type"})': {
            ("bioetl-runtime.json", "Runtime Status"),
            ("bioetl-runtime.json", "Status"),
        },
    }


def _assert_dq_duplicate_reuse_semantics() -> None:
    dq_dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    dq_panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dq_dashboard)
        if panel.get("title")
    }
    score_summary = dq_panels["Monitor: Data Quality Score (Volume-weighted)"]
    score_trend = dq_panels["Track: Data Quality Score Trend (Volume-weighted)"]
    assert score_summary.get("type") == "stat"
    assert score_summary.get("options", {}).get("colorMode") == "value"
    assert score_summary.get("options", {}).get("graphMode") == "none"
    summary_defaults = score_summary.get("fieldConfig", {}).get("defaults", {})
    assert summary_defaults.get("unit") == "percentunit"
    assert summary_defaults.get("min") == 0
    assert summary_defaults.get("max") == 1
    assert summary_defaults.get("thresholds", {}).get("steps") == [
        {"color": "red", "value": None},
        {"color": "orange", "value": 0.8},
        {"color": "green", "value": 0.95},
    ]
    assert score_trend.get("type") == "timeseries"
    assert score_trend.get("options", {}).get("tooltip", {}).get("mode") == "single"
    assert "review trend" in str(score_summary.get("description", "")).lower()
    assert (
        "trend over selected time range"
        in str(score_trend.get("description", "")).lower()
    )


def _assert_lineage_control_plane_ownership_handoff() -> None:
    dq_dashboard = load_dashboard(Path("grafana/dashboards/bioetl-dq-v2.json"))
    control_plane_dashboard = load_dashboard(
        Path("grafana/dashboards/bioetl-control-plane-v1.json")
    )
    dq_panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(dq_dashboard)
        if panel.get("title")
    }
    control_plane_panels = {
        panel.get("title"): panel
        for panel in get_dashboard_panels(control_plane_dashboard)
        if panel.get("title")
    }
    dq_handoff = dq_panels["Review: Lineage Handoff to Control Plane"]
    control_plane_lineage = control_plane_panels["Monitor: Lineage Refs Missing"]
    assert dq_handoff.get("type") == "text"
    dq_content = str(dq_handoff.get("options", {}).get("content", "")).lower()
    assert "control plane" in dq_content
    assert "canonical" in dq_content
    dq_links = list(dq_handoff.get("links") or [])
    assert any(
        "bioetl-control-plane-v1" in str(link.get("url", ""))
        and "viewPanel=904" in str(link.get("url", ""))
        for link in dq_links
    )
    assert control_plane_lineage.get("options", {}).get("graphMode") == "area"
    assert (
        "missing lineage can make replay evidence incomplete"
        in str(control_plane_lineage.get("description", "")).lower()
    )


def test_exact_duplicate_promql_groups_are_only_explicitly_justified_reuse() -> None:
    """Exact duplicate PromQL must stay limited to audited, role-justified reuse."""
    observed_uses_by_expr: dict[str, set[tuple[str, str]]] = {}

    for dashboard_path in get_dashboard_files():
        dashboard = load_dashboard(dashboard_path)
        for panel in get_dashboard_panels(dashboard):
            title = panel.get("title")
            if not isinstance(title, str):
                continue
            for target in panel.get("targets", []):
                expr = target.get("expr")
                if not isinstance(expr, str) or not expr.strip():
                    continue
                normalized_expr = " ".join(expr.split())
                observed_uses_by_expr.setdefault(normalized_expr, set()).add(
                    (dashboard_path.name, title)
                )

    duplicate_uses_by_expr = {
        expr: uses for expr, uses in observed_uses_by_expr.items() if len(uses) > 1
    }
    expected_duplicate_uses = _expected_duplicate_uses()
    assert duplicate_uses_by_expr == expected_duplicate_uses, (
        "Dashboard exact PromQL duplication drifted outside the audited allowlist: "
        f"{duplicate_uses_by_expr}"
    )
    _assert_dq_duplicate_reuse_semantics()
    _assert_lineage_control_plane_ownership_handoff()
