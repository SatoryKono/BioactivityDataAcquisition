"""Shadow-compare route coverage for RF-002 evidence-location surfaces."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.engineering.ci.pr_lane_results import build_shadow_compare

pytestmark = pytest.mark.unit


def test_shadow_compare_routes_run_report_contracts_and_docs__rf002_routes() -> None:
    """Run-report and resource-review inputs select their contract tests."""
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [
            "configs/contracts/reports/run_evidence_location.v1.json",
            "tests/fixtures/reports/run_evidence_location_golden.json",
            "docs/04-reference/reports/run-reports.md",
            "configs/quality/external_resource_inventory_pr12755_review.json",
        ],
        repo_root=repo_root,
    )
    assert report["covers_full_suite"] is False
    assert "tests/unit/domain/run_reports/test_contracts.py" in report["selected"]
    assert (
        "tests/unit/domain/control_plane/test_run_evidence_location.py"
        in report["selected"]
    )
    assert "tests/architecture/test_documentation_sync.py" in report["selected"]
    assert (
        "tests/architecture/test_external_resource_inventory_catalog.py"
        in report["selected"]
    )
    assert (
        "tests/unit/scripts/engineering/qa/test_requalify_external_resource_inventory.py"
        in report["selected"]
    )


@pytest.mark.parametrize(
    "path",
    (
        "reports/qm07/acceptance.md",
        "reports/qm07/passport.md",
    ),
)
def test_shadow_compare_routes_qm07_closeout_evidence(path: str) -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare([path], repo_root=root)
    assert report["selected"] == [
        "tests/architecture/test_qm07_cold_imports.py",
    ]


def test_shadow_compare_routes_domain_ports_stub__rf002_routes() -> None:
    """Typed ports package stubs map like their .py siblings under tests/unit."""
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        ["src/bioetl/domain/ports/__init__.pyi"],
        repo_root=repo_root,
    )
    assert report["covers_full_suite"] is False
    assert "tests/unit/domain" in report["selected"]
