"""Focused shadow routing for stubs, ratchets, and diagram tooling paths."""

from __future__ import annotations

from pathlib import Path

import pytest
from scripts.engineering.ci.pr_lane_results import build_shadow_compare

pytestmark = pytest.mark.unit


def test_shadow_compare_routes_domain_ports_stub_from_registry() -> None:
    """Typed ports package stubs map like their .py siblings under tests/unit."""
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        ["src/bioetl/domain/ports/__init__.pyi"],
        repo_root=repo_root,
    )
    assert report["covers_full_suite"] is False
    assert "tests/unit/domain" in report["selected"]


def test_shadow_compare_routes_assertless_ratchet_config() -> None:
    """The shrink-only assertless ratchet has explicit owning tests."""
    repo_root = Path(__file__).resolve().parents[5]

    report = build_shadow_compare(
        ["configs/quality/assertless_ratchet.yaml"],
        repo_root=repo_root,
    )

    assert report["selected"] == [
        "tests/architecture/test_arch_s4_s9_gates.py",
        "tests/architecture/test_test_governance_audit.py",
        "tests/architecture/test_tech_debt_issues_5514_5515_governance.py",
    ]


def test_shadow_compare_routes_diagram_runner_paths() -> None:
    """Diagram tooling changes select their runner and budget contracts."""
    repo_root = Path(__file__).resolve().parents[5]

    report = build_shadow_compare(
        ["scripts/diagrams/README.md", "scripts/diagrams/run_diagram_checks.sh"],
        repo_root=repo_root,
    )

    assert report["selected"] == [
        "tests/architecture/test_diagram_quality_budget_security.py",
        "tests/architecture/test_run_diagram_checks_script.py",
        "tests/architecture/test_diagram_issues_6205_6211_closeout.py",
    ]
