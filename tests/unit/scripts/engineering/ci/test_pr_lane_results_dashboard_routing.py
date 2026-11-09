"""Focused shadow-compare routing for dashboard docs and shipped JSON."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.engineering.ci.pr_lane_results import build_shadow_compare

pytestmark = pytest.mark.unit


def test_shadow_compare_routes_dashboard_docs_and_json() -> None:
    """Dashboard contracts and shipped JSON select their governing tests."""
    root = Path(__file__).resolve().parents[5]
    changed = [
        "docs/03-guides/dashboards/contracts/selector-contracts.yaml",
        "docs/03-guides/dashboards/selector-architecture.md",
        "docs/03-guides/dashboards/variable-reference.md",
        "grafana/dashboards/bioetl-control-plane-v1.json",
        "grafana/dashboards/bioetl-dq-v2.json",
        "grafana/dashboards/bioetl-incident-v1.json",
        "grafana/dashboards/bioetl-overview-v2.json",
        "grafana/dashboards/bioetl-run-explorer-v1.json",
    ]
    report = build_shadow_compare(changed, repo_root=root)
    assert "tests/architecture/test_documentation_sync.py" in report["selected"]
    assert "tests/architecture/test_dashboard_scenes_contract.py" in report["selected"]
    assert "tests/integration/test_grafana_selector_contract.py" in report["selected"]
    assert (
        "tests/integration/test_dashboard_variable_dependencies.py"
        in report["selected"]
    )


@pytest.mark.parametrize(
    "path",
    [
        "configs/quality/promql_max_over_time_counter_policy.yaml",
        "docs/05-operations/runbooks/pipeline-failure-dq.md",
        "docs/03-guides/dashboards/panel-contract-inventory.json",
        "grafana/prometheus-rules/bioetl_observability.yml",
        "grafana/prometheus-rules/bioetl_workflow_scope.yml",
        "grafana/prometheus-rules/tests/bioetl_observability.test.yml",
        "grafana/prometheus-rules/tests/workflow_selector_isolation.test.yml",
    ],
)
def test_observability_remediation_paths_have_strict_test_routes(path: str) -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare([path], repo_root=root)
    assert "tests/integration/test_prometheus_rules_config.py" in report["selected"]
    assert (
        "tests/architecture/test_observability_metric_governance.py"
        in report["selected"]
    )
