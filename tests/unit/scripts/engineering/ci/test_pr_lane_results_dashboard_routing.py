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
