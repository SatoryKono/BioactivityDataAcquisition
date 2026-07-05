"""Architecture checks for quality-governance CI gate policy."""

from __future__ import annotations

import pytest

from pathlib import Path


pytestmark = pytest.mark.architecture


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


def test_tests_workflow_runs_debt_governance_closeout_gates() -> None:
    """Merge pipeline must validate ADR, remote-main, and debt-governance artifacts."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "Validate ADR enforcement matrix artifacts" in workflow
    assert "report-adr-enforcement-matrix --check" in workflow
    assert "Validate remote-main architecture debt baseline" in workflow
    assert (
        "git fetch --no-tags --depth=1 origin main:refs/remotes/origin/main" in workflow
    )
    assert "report-architecture-debt-remote-main-baseline --check" in workflow
    assert "Validate debt-governance fail-fast gates" in workflow
    assert "report-debt-governance-gates --check" in workflow


def test_tests_workflow_runs_generated_architecture_evidence_gates() -> None:
    """Merge pipeline must validate generated architecture evidence artifacts."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "Validate contract coverage matrix artifact" in workflow
    assert "report-contract-coverage-matrix --check" in workflow
    assert "Validate port-adapter-factory coverage map artifact" in workflow
    assert "report-port-adapter-factory-coverage --check" in workflow
    assert "Validate domain aggregate invariant registry" in workflow
    assert "tests/architecture/test_domain_aggregate_invariant_registry.py" in workflow


def test_read_only_architecture_audit_covers_generated_evidence_gates() -> None:
    """Read-only architecture audit must include generated evidence drift gates."""
    from scripts.engineering.qa.run_architecture_audit_read_only import (
        architecture_audit_checks,
    )

    checks = {check.name: check for check in architecture_audit_checks()}
    check_names = set(checks)
    module_coverage_command = checks["module_coverage_inventory"].command
    assert "contract_coverage_matrix" in check_names
    assert "port_adapter_factory_coverage" in check_names
    assert "observability_metric_inventory" in check_names
    assert "domain_aggregate_invariant_registry" in check_names
    assert "module_coverage_inventory" in check_names
    assert "debt_governance_gates" in check_names
    assert "--allow-missing-coverage-xml" in module_coverage_command


def test_tests_workflow_enforces_dead_code_inventory_drift_gate() -> None:
    """Merge pipeline must fail fast when dead-code evidence artifacts drift."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "Validate dead-code inventory artifacts" in workflow
    assert (
        "python -m scripts.engineering.qa report-dead-code-inventory --check"
        in workflow
    )


def test_tests_workflow_enforces_test_governance_snapshot_gate() -> None:
    """Merge pipeline must fail fast when test-governance artifacts drift."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "Validate committed test-governance snapshots" in workflow
    assert "python -m scripts.engineering.qa.report_test_governance_audit" in workflow
    assert "reports/quality/test-governance-current.json" in workflow
    assert "reports/quality/test-duplicate-name-inventory.json" not in workflow


def test_tests_workflow_runs_observability_cardinality_review_gate() -> None:
    """Merge pipeline must emit explicit runtime-cardinality review evidence."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "Review observability runtime cardinality evidence" in workflow
    assert "report-observability-metric-inventory" in workflow
    assert "reports/observability/runtime_cardinality_inventory.json" in workflow
    assert "reports/observability/runtime_cardinality_review.json" in workflow
    assert "BIOETL_OBSERVABILITY_PROMETHEUS_URL" in workflow
    assert "BIOETL_OBSERVABILITY_PROMETHEUS_TOKEN" in workflow
    assert "GITHUB_STEP_SUMMARY" in workflow
    assert "--fail-on-degraded-live-review" in workflow


def test_tests_workflow_uploads_observability_cardinality_review_artifacts() -> None:
    """Cardinality review JSON artifacts must be uploaded even on degraded runs."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "Upload observability review artifacts" in workflow
    assert "name: observability-runtime-cardinality-review" in workflow
    assert "reports/observability/runtime_cardinality_inventory.json" in workflow
    assert "reports/observability/runtime_cardinality_review.json" in workflow


def test_tests_workflow_routes_coverage_xml_under_reports() -> None:
    """Coverage XML must be generated and uploaded from reports/coverage."""
    workflow = Path(".github/workflows/tests.yml").read_text(encoding="utf-8")
    assert "coverage xml -o reports/coverage/coverage.xml" in workflow
    assert "name: coverage-report" in workflow
    assert "reports/coverage/coverage.xml" in workflow
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
