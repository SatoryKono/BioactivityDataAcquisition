"""Architecture checks for quality-governance CI gate policy."""

from __future__ import annotations

from pathlib import Path


def test_tests_workflow_blocks_expired_exemptions() -> None:
    """Merge pipeline must block when expired exemptions are present."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "QUALITY_EXEMPTIONS_GATE_MODE: block" in workflow


def test_tests_workflow_uses_staged_growth_rollout_mode() -> None:
    """Growth gate mode should be auto to honor scorecard staged rollout policy."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "QUALITY_EXEMPTIONS_GROWTH_MODE: auto" in workflow


def test_tests_workflow_enforces_budget_only_temp_windows() -> None:
    """Temporary exemption windows must stay budget-only and timeboxed in CI."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "QUALITY_EXEMPTIONS_TEMP_WINDOW_MODE: budget-only" in workflow
    assert "QUALITY_EXEMPTIONS_MAX_GRACE_WINDOW_DAYS: 45" in workflow
    assert "--temp-window-mode" in workflow
    assert "--max-grace-window-days" in workflow


def test_tests_workflow_prints_quality_exemption_trend_report() -> None:
    """CI should emit burn-down trend report for ratchet-only registries."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "--trend-report on" in workflow


def test_tests_workflow_has_fail_fast_quality_ratchet_profile() -> None:
    """CI must run staged architecture debt ratchet in strict layer order."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "Quality ratchet (fail-fast: domain)" in workflow
    assert "Quality ratchet (fail-fast: application)" in workflow
    assert "Quality ratchet (fail-fast: infrastructure)" in workflow

    domain_pos = workflow.index("Quality ratchet (fail-fast: domain)")
    app_pos = workflow.index("Quality ratchet (fail-fast: application)")
    infra_pos = workflow.index("Quality ratchet (fail-fast: infrastructure)")
    assert domain_pos < app_pos < infra_pos


def test_tests_workflow_runs_ci_quality_integral_gate() -> None:
    """Merge pipeline must run the canonical CI quality debt gate and publish JSON."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "quality-metrics-gate" in workflow
    assert "make qa-debt" in workflow
    assert "reports/quality/ci-quality-metrics.json" in workflow
    assert 'QUALITY_SUMMARY_OUT="$GITHUB_STEP_SUMMARY"' in workflow


def test_tests_workflow_routes_coverage_xml_under_reports() -> None:
    """Coverage XML must be generated and uploaded from reports/coverage."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "coverage xml -o reports/coverage/coverage.xml" in workflow
    assert "path: reports/coverage/coverage.xml" in workflow
    assert "coverage xml -o coverage.xml" not in workflow
    assert "path: coverage.xml" not in workflow


def test_tests_workflow_enforces_scripts_lifecycle_governance() -> None:
    """Merge pipeline must validate scripts inventory drift + lifecycle policy."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "python -m scripts.engineering.repo check-inventory" in workflow
    assert "configs/quality/scripts_inventory_manifest.json" in workflow
    assert "configs/quality/scripts_lifecycle_registry.json" in workflow
    assert "--forbid-evaluate-active" in workflow


def test_tests_workflow_enforces_scripts_catalog_governance() -> None:
    """Merge pipeline must validate scripts catalog policy."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "python -m scripts.engineering.repo check-catalog" in workflow
    assert "scripts/engineering/repo/catalog.yaml" in workflow


def test_pretest_guardrails_enforce_generated_artifact_routing() -> None:
    """Pretest governance profile must block unsafe generated artifact routes."""
    guardrails = Path("configs/quality/pretest_guardrails.yaml").read_text(
        encoding="utf-8"
    )
    assert "tests/architecture/test_generated_artifact_routing.py" in guardrails
