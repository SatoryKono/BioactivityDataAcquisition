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
"""Golden contracts for shipped Grafana dashboard JSON."""

from __future__ import annotations

import pytest

import json
import re
from pathlib import Path

import yaml

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
DASHBOARD_DIR = ROOT / "grafana" / "dashboards"
ALLOWLIST_PATH = ROOT / "configs" / "quality" / "dashboard_promql_scope_allowlist.yaml"
DASHBOARD_INVENTORY_PATH = (
    ROOT
    / "docs"
    / "03-guides"
    / "dashboards"
    / "contracts"
    / "dashboard-inventory.yaml"
)

_DQ_VERDICT_RATIO_RE = re.compile(
    r"records_processed_total\{[^}]*stage\s*=\s*\"(?:filtered_out|bronze)\"[^}]*\}"
    r".*\/\s*clamp_min\(",
    re.DOTALL,
)
_DQ_BLOCKED_RATIO_RE = re.compile(
    r"dq_records_quarantined_total.*\/\s*clamp_min\(",
    re.DOTALL,
)
_PROMQL_METRIC_SELECTOR_RE = re.compile(r"([a-zA-Z_:][a-zA-Z0-9_:]*)\{([^{}]*)\}")
_FORBIDDEN_DASHBOARD_TOKENS = ("checkpoint_saved_at_epoch_seconds",)


def _load_allowlist() -> tuple[frozenset[str], frozenset[str]]:
    payload = yaml.safe_load(ALLOWLIST_PATH.read_text(encoding="utf-8"))
    metrics = frozenset(
        str(item) for item in payload.get("metrics_without_run_type_label", [])
    )
    dashboards = frozenset(
        str(item) for item in payload.get("pipeline_summary_dashboards", [])
    )
    return metrics, dashboards


def _iter_panels(dashboard: dict[str, object]) -> list[dict[str, object]]:
    panels: list[dict[str, object]] = []
    for panel in dashboard.get("panels", []):
        if not isinstance(panel, dict):
            continue
        panels.append(panel)
        if panel.get("type") == "row":
            for nested in panel.get("panels", []):
                if isinstance(nested, dict):
                    panels.append(nested)
    return panels


def _panel_expressions(panel: dict[str, object]) -> list[str]:
    expressions: list[str] = []
    for target in panel.get("targets", []):
        if not isinstance(target, dict):
            continue
        expr = target.get("expr", "")
        if isinstance(expr, str) and expr.strip():
            expressions.append(expr)
    return expressions


def test_all_shipped_dashboards_have_bounded_owner_routes() -> None:
    """Every shipped dashboard must route ownership to one reviewed runbook."""
    payload = yaml.safe_load(DASHBOARD_INVENTORY_PATH.read_text(encoding="utf-8"))
    dashboards = payload["dashboards"]
    assert {dashboard["uid"] for dashboard in dashboards} == {
        path.stem for path in DASHBOARD_DIR.glob("*.json")
    }

    allowed_owners = {"@bioetl-observability"}
    allowed_routes = {
        "docs/05-operations/runbooks/observability-checklist.md",
        "docs/05-operations/runbooks/run-manifest-inspection.md",
        "docs/05-operations/runbooks/pipeline-failure-critical.md",
        "docs/05-operations/runbooks/incident-response.md",
        "docs/05-operations/runbooks/dq-failure-investigation.md",
        "docs/05-operations/runbooks/quarantine-management.md",
    }
    for dashboard in dashboards:
        assert dashboard["owner"] in allowed_owners
        route = str(dashboard["owner_route"])
        assert route in allowed_routes
        assert (ROOT / route).is_file(), f"Missing owner route: {route}"


def test_alerts_slo_panels_one_through_five_link_reviewed_owner_runbook() -> None:
    """The alert decision surface must expose a direct owner/runbook handoff."""
    dashboard_path = DASHBOARD_DIR / "bioetl-alerts-slo.json"
    if not dashboard_path.is_file():
        pytest.skip("bioetl-alerts-slo.json retired from shipping surface (epic #6647)")
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    panels = {int(panel["id"]): panel for panel in _iter_panels(dashboard)}
    for panel_id in range(1, 6):
        links = panels[panel_id].get("links", [])
        assert len(links) == 1
        link = links[0]
        assert link["title"] == "Runbook · @bioetl-observability"
        assert link["url"].endswith(
            "/docs/05-operations/runbooks/observability-checklist.md"
        )
        assert link["includeVars"] is False


def test_dashboard_json_must_not_reference_deprecated_checkpoint_alias() -> None:
    offenders: list[str] = []
    for dashboard_path in sorted(DASHBOARD_DIR.glob("*.json")):
        if dashboard_path.name.endswith(".backup"):
            continue
        content = dashboard_path.read_text(encoding="utf-8")
        for token in _FORBIDDEN_DASHBOARD_TOKENS:
            if token in content:
                offenders.append(f"{dashboard_path.name}: {token}")
    assert not offenders, "\n".join(offenders)


def test_dq_dashboard_must_not_use_hardcoded_blocked_share_verdict_math() -> None:
    dashboard = json.loads(
        (DASHBOARD_DIR / "bioetl-dq-v2.json").read_text(encoding="utf-8")
    )
    verdict_titles = {
        "Status",
        "Monitor DQ Current Status",
        "Now · DQ Threshold State",
    }
    offenders: list[str] = []
    for panel in _iter_panels(dashboard):
        title = str(panel.get("title", ""))
        if title in verdict_titles:
            continue
        for expr in _panel_expressions(panel):
            if _DQ_BLOCKED_RATIO_RE.search(expr.replace("\n", " ")):
                offenders.append(f"{title}: blocked-share ratio in PromQL")
            if (
                "filtered_out" in expr
                and 'stage="bronze"' in expr
                and "/ clamp_min(" in expr
                and title.startswith(("Monitor:", "Track: DQ Impact"))
            ):
                offenders.append(f"{title}: deliverability ratio verdict math")
    assert not offenders, "\n".join(offenders)


def test_dq_quarantine_count_is_shipped_in_range_evidence_lane() -> None:
    dashboard = json.loads(
        (DASHBOARD_DIR / "bioetl-dq-v2.json").read_text(encoding="utf-8")
    )
    # Diet surface (#6647): quarantine evidence is shipped as blocked-records panel.
    accepted_titles = {
        "Range · Records Quarantined",
        "Track: DQ Blocked Records in Range (Evidence)",
    }
    range_lane = next(
        (
            item
            for item in dashboard.get("panels", [])
            if item.get("title") == "Range lane · debug evidence"
        ),
        None,
    )
    assert range_lane is not None
    panel = next(
        (
            item
            for item in range_lane.get("panels", [])
            if item.get("title") in accepted_titles
        ),
        None,
    )
    assert panel is not None
    assert panel.get("type") != "row"


def test_pipeline_summary_dashboards_apply_run_type_to_labelled_metrics() -> None:
    from tests.integration._grafana_test_support import get_metric_label_sets

    allowlist, pipeline_summary = _load_allowlist()
    label_sets = get_metric_label_sets()
    offenders: list[str] = []

    for dashboard_name in sorted(pipeline_summary):
        dashboard_path = DASHBOARD_DIR / dashboard_name
        dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
        for panel in _iter_panels(dashboard):
            title = str(panel.get("title", ""))
            for expr in _panel_expressions(panel):
                for metric_name, selector_body in _PROMQL_METRIC_SELECTOR_RE.findall(
                    expr
                ):
                    if metric_name in allowlist:
                        continue
                    expected_labels = label_sets.get(metric_name)
                    if expected_labels is None or "run_type" not in expected_labels:
                        continue
                    if "run_type" not in selector_body:
                        offenders.append(
                            f"{dashboard_name} :: {title} :: {metric_name} missing run_type filter"
                        )
    assert not offenders, "\n".join(offenders[:20])


def test_provider_health_provenance_documents_provider_global_scope() -> None:
    dashboard = json.loads(
        (DASHBOARD_DIR / "bioetl-provider-health-v2.json").read_text(encoding="utf-8")
    )
    provenance = next(
        (
            panel
            for panel in dashboard.get("panels", [])
            if panel.get("title") == "Provenance"
        ),
        None,
    )
    assert provenance is not None
    content = str(provenance.get("options", {}).get("content", ""))
    assert "Provider-global" in content or "provider-global" in content.lower()
    assert "Runtime" in content


def test_workflow_overview_exposes_failed_pipeline_run_handoff() -> None:
    dashboard_path = DASHBOARD_DIR / "bioetl-workflow-overview.json"
    if not dashboard_path.is_file():
        pytest.skip(
            "bioetl-workflow-overview.json retired from shipping surface (epic #6647)"
        )
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    titles = {str(panel.get("title", "")) for panel in _iter_panels(dashboard)}
    assert "Failed Entity Pipeline Runs / Range" in titles


def test_workflow_overview_exposes_fail_closed_pipeline_status_verdict() -> None:
    dashboard_path = DASHBOARD_DIR / "bioetl-workflow-overview.json"
    if not dashboard_path.is_file():
        pytest.skip(
            "bioetl-workflow-overview.json retired from shipping surface (epic #6647)"
        )
    dashboard = json.loads(dashboard_path.read_text(encoding="utf-8"))
    panel = next(
        (
            item
            for item in _iter_panels(dashboard)
            if item.get("title") == "Pipeline Status"
        ),
        None,
    )
    assert panel is not None
    assert panel.get("type") == "stat"
    assert "bioetl_workflow_pipeline_verdict_status" in " ".join(
        _panel_expressions(panel)
    )
    assert "run_id" not in " ".join(_panel_expressions(panel))
    data_links = panel.get("options", {}).get("dataLinks", [])
    link_titles = {str(link.get("title")) for link in data_links}
    assert {"Open 2. Runtime", "Open 0. Control Plane"} <= link_titles


def test_batch_status_aggregate_is_not_synthesized_as_runtime_metric() -> None:
    forbidden_metric = "bioetl_" + "batch_status"
    rules = (
        ROOT / "grafana" / "prometheus-rules" / "bioetl_observability.yml"
    ).read_text(encoding="utf-8")
    dashboards = "\n".join(
        path.read_text(encoding="utf-8") for path in DASHBOARD_DIR.glob("*.json")
    )
    assert forbidden_metric not in rules
    assert forbidden_metric not in dashboards
    observability_contract = (
        ROOT / "docs" / "04-reference" / "contracts" / "observability.md"
    ).read_text(encoding="utf-8")
    assert "BatchStatus aggregate is non-runtime" in observability_contract
