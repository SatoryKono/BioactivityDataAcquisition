"""Unit tests for coordinator job-result mapping."""

from __future__ import annotations

import json
import subprocess
from collections.abc import Sequence
from pathlib import Path

import pytest
from scripts.engineering.ci.pr_lane_results import (
    OWNER_STEPS,
    affected_pytest_targets,
    assert_step_outcomes,
    build_results,
    build_shadow_compare,
    main as lane_main,
    plan_affected_subtraction,
)

pytestmark = pytest.mark.unit

HEAD = "a" * 40


def test_not_applicable_gate_does_not_inherit_job_success() -> None:
    """Keep a nonapplicable gate skipped even when its owner job succeeds."""
    results = build_results(
        {
            "docs-governance": {
                "decision": "not_applicable",
                "reason": "no_path_match",
            }
        },
        {"fast-governance": "success"},
        head_sha=HEAD,
    )

    assert results["docs-governance"] == {
        "required": "skipped",
        "not_applicable": "success",
        "na_head_sha": HEAD,
        "na_reason": "no_path_match",
    }


def test_required_gate_is_red_when_owner_job_is_skipped() -> None:
    """Keep required evidence missing when the owning CI job is skipped."""
    results = build_results(
        {"tests": {"decision": "required", "reason": "path_match"}},
        {"class-lane": "skipped"},
        head_sha=HEAD,
    )

    assert results["tests"]["required"] == "skipped"
    assert results["tests"]["not_applicable"] == "skipped"


def test_required_gate_passes_only_when_owner_job_succeeds() -> None:
    """Map a successful owner job to a successful required gate."""
    results = build_results(
        {"lint-arch": {"decision": "required", "reason": "path_match"}},
        {"class-lane": "success"},
        head_sha=HEAD,
    )

    assert results["lint-arch"]["required"] == "success"


def test_cancelled_job_is_failure() -> None:
    """Treat a cancelled owner job as failure for its required gate."""
    results = build_results(
        {"security": {"decision": "required", "reason": "path_match"}},
        {"class-lane": "cancelled"},
        head_sha=HEAD,
    )

    assert results["security"]["required"] == "failure"


def test_assert_steps_ignores_not_applicable_gates() -> None:
    """Allow missing step evidence for gates classified as nonapplicable."""
    failures = assert_step_outcomes(
        {"docker": {"decision": "not_applicable", "reason": "no_path_match"}},
        {},
        owner="class-lane",
    )

    assert failures == []


def test_docs_governance_requires_docs_lane_jobs() -> None:
    """A selected docs-governance gate fails when an owner job outcome is skipped."""
    failures = assert_step_outcomes(
        {"docs-governance": {"decision": "required", "reason": "path_match"}},
        {
            "docs-governance": "success",
            "validate-mkdocs": "success",
            "check-diagram-drift": "skipped",
        },
        owner="docs-lane",
    )

    assert failures == ["docs-governance:check-diagram-drift=skipped"]


def test_assert_steps_fails_when_required_step_is_skipped() -> None:
    """Report a skipped required type-checking step as a failure."""
    failures = assert_step_outcomes(
        {"type-checking": {"decision": "required", "reason": "path_match"}},
        {
            "mypy": "skipped",
            "newtype-protocol": "success",
            "any-usage": "success",
        },
        owner="class-lane",
    )

    assert failures == ["type-checking:mypy=skipped"]


def test_assert_steps_fails_on_unrelated_step_failure() -> None:
    """Report failed job steps even when all required gate steps pass."""
    failures = assert_step_outcomes(
        {"type-checking": {"decision": "required", "reason": "path_match"}},
        {
            "mypy": "success",
            "newtype-protocol": "success",
            "any-usage": "success",
            "checkout": "failure",
        },
        owner="class-lane",
    )

    assert "step:checkout=failure" in failures


def test_empty_diff_selects_full_python_suite() -> None:
    """An empty diff still has a required tests gate, so run the whole suite."""
    repo_root = Path(__file__).resolve().parents[5]
    assert affected_pytest_targets([], repo_root=repo_root) == ["tests"]
    assert affected_pytest_targets(["   "], repo_root=repo_root) == ["tests"]


def test_empty_diff_fails_closed_when_suite_root_is_missing(tmp_path: Path) -> None:
    """A missing tests tree cannot satisfy the empty-diff tests gate."""
    with pytest.raises(ValueError, match="Missing mandatory mapped test targets"):
        affected_pytest_targets([], repo_root=tmp_path)


def test_empty_diff_cli_prints_full_suite(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The lane command must emit the full suite when git reports no paths."""
    from scripts.engineering.ci import pr_lane_results as lane

    def _empty_diff(
        *_args: object, **_kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=["git"], returncode=0, stdout="")

    monkeypatch.setattr(lane.subprocess, "run", _empty_diff)
    repo_root = Path(__file__).resolve().parents[5]
    assert (
        lane_main(
            [
                "affected-tests",
                "--repo-root",
                str(repo_root),
                "--base-sha",
                HEAD,
                "--head-sha",
                HEAD,
            ]
        )
        == 0
    )
    assert capsys.readouterr().out.splitlines() == ["tests"]


def test_shadow_compare_records_selection_without_activation(tmp_path: Path) -> None:
    """Shadow mode records a narrow selection and does not mark it activated."""
    unit_domain = tmp_path / "tests" / "unit" / "domain"
    unit_domain.mkdir(parents=True)
    (unit_domain / "test_sample.py").write_text(
        "def test_sample():\n    assert True\n",
        encoding="utf-8",
    )

    report = build_shadow_compare(
        ["tests/unit/domain/test_sample.py"],
        repo_root=tmp_path,
    )

    assert report == {
        "activation": "not_applied",
        "covers_full_suite": False,
        "full_suite_root": "tests",
        "mode": "shadow",
        "selected": ["tests/unit/domain/test_sample.py"],
        "selected_count": 1,
    }


def test_shadow_compare_routes_domain_layer_doc() -> None:
    """Domain layer doc edits keep a fail-closed impact route."""
    repo_root = Path(__file__).resolve().parents[5]

    report = build_shadow_compare(
        ["docs/02-architecture/01-domain-layer.md"],
        repo_root=repo_root,
    )

    assert report["selected"] == [
        "tests/architecture/test_documentation_sync.py",
        "tests/architecture/test_domain_io_taint_inventory.py",
    ]
    assert report["covers_full_suite"] is False


def test_shadow_compare_routes_billing_pr_non_code_changes() -> None:
    """Billing documentation and its manifest have explicit test routes."""
    repo_root = Path(__file__).resolve().parents[5]

    report = build_shadow_compare(
        [
            "CHANGELOG.md",
            "docs/02-architecture/finances-github-billing.md",
            "reports/engineering/finances/billing_manifest.json",
        ],
        repo_root=repo_root,
    )

    assert "tests/architecture/test_docs_version_sync.py" in report["selected"]
    assert "tests/architecture/test_documentation_sync.py" in report["selected"]
    assert "tests/unit/scripts/test_github_billing.py" in report["selected"]


def test_shadow_compare_routes_epoch2208_variant_b_evidence() -> None:
    """Variant B evidence selects the cleanup-inventory contract."""
    repo_root = Path(__file__).resolve().parents[5]

    report = build_shadow_compare(
        [
            "reports/epoch2208/b/12371_b_handoff.md",
            "reports/epoch2208/b/architecture_collection.txt",
        ],
        repo_root=repo_root,
    )

    assert report["selected"] == [
        "tests/architecture/test_documentation_cleanup_inventory.py"
    ]
    assert report["covers_full_suite"] is False


def test_shadow_compare_routes_12375_a_evidence() -> None:
    """Issue 12375 A evidence selects the cleanup-inventory contract."""
    repo_root = Path(__file__).resolve().parents[5]

    report = build_shadow_compare(
        [
            "reports/engineering/12375-a/consumers.md",
            "reports/engineering/12375-a/handoff.md",
            "reports/engineering/12375-a/profile_summary.md",
        ],
        repo_root=repo_root,
    )

    assert report["selected"] == [
        "tests/architecture/test_documentation_cleanup_inventory.py"
    ]
    assert report["covers_full_suite"] is False


def test_shadow_compare_routes_historical_secret_fingerprints() -> None:
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare([".gitleaksignore"], repo_root=repo_root)
    assert report["selected"] == [
        "tests/architecture/test_secret_shape_and_operator_guide_contracts.py"
    ]
    assert report["covers_full_suite"] is False


@pytest.mark.parametrize(
    "path",
    (
        "configs/composites/activity.yaml",
        "configs/composites/target.yaml",
        "configs/composites/field_groups/shared_policy.yaml",
    ),
)
def test_shadow_compare_routes_composite_configs(path: str) -> None:
    """Every composite YAML selects the schema test that loads the family."""
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare([path], repo_root=repo_root)
    assert (
        "tests/unit/infrastructure/schemas/test_composite_config_schema.py"
        in report["selected"]
    )


@pytest.mark.parametrize(
    "path",
    (
        "configs/entities/chembl/activity.yaml",
        "configs/entities/chembl/target.yaml",
        "configs/entities/pubchem/compound.yaml",
    ),
)
def test_shadow_compare_routes_entity_configs(path: str) -> None:
    """Every entity YAML selects fail-closed pipeline load + filter schema tests."""
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare([path], repo_root=repo_root)
    assert "tests/architecture/test_config_strict_keys.py" in report["selected"]
    assert (
        "tests/unit/infrastructure/schemas/test_filter_config.py" in report["selected"]
    )


def test_shadow_compare_routes_published_pipeline_schemas() -> None:
    """Published pipeline JSON schemas select the tests that read them."""
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [
            "configs/_schema/composite.json",
            "configs/_schema/pipeline.json",
        ],
        repo_root=repo_root,
    )
    assert (
        "tests/architecture/test_config_schema_migration_status.py"
        in report["selected"]
    )
    assert (
        "tests/integration/config/test_validate_pipeline_configs.py"
        in report["selected"]
    )
    assert (
        "tests/unit/repo_backed/infrastructure/config/test_composite_sort_by_closure.py"
        in report["selected"]
    )


def test_shadow_compare_routes_published_dq_schema() -> None:
    """The published DQ JSON schema selects the tests that read it."""
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        ["configs/_schema/dq.json"],
        repo_root=repo_root,
    )
    assert report["covers_full_suite"] is False
    assert report["selected"] == [
        "tests/architecture/test_config_schema_migration_status.py",
        "tests/unit/infrastructure/schemas/test_dq_config.py",
    ]


def test_shadow_compare_routes_docker_and_remote_main_report() -> None:
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [
            ".github/workflows/docker.yml",
            "reports/quality/architecture-debt-remote-main-baseline.md",
        ],
        repo_root=repo_root,
    )
    assert "tests/architecture/test_docker_runtime_contracts.py" in report["selected"]
    assert (
        "tests/unit/scripts/qa/test_report_architecture_debt_remote_main_baseline.py"
        in report["selected"]
    )


@pytest.mark.parametrize("workflow", ["codeql.yml", "tests.yml", "release.yml"])
def test_shadow_compare_routes_reviewed_workflow_contracts(workflow: str) -> None:
    """Reviewed workflows select the validator that scans their action refs."""
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [f".github/workflows/{workflow}"], repo_root=repo_root
    )
    assert report["selected"] == [
        "tests/architecture/test_github_actions_runtime_policy.py"
    ]
    with pytest.raises(ValueError, match="unmapped paths"):
        build_shadow_compare(
            [".github/workflows/unreviewed-new-workflow.yml"], repo_root=repo_root
        )


@pytest.mark.parametrize("manifest", ["package.json", "package-lock.json"])
def test_shadow_compare_routes_gemini_toolchain(manifest: str) -> None:
    """Each toolchain manifest independently selects the integrity contract."""
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [f"scripts/ai/gemini/npm-tooling/{manifest}"], repo_root=repo_root
    )
    assert report["selected"] == ["tests/architecture/test_gemini_cli_bootstrap.py"]


def test_shadow_compare_routes_grafana_npm_projects() -> None:
    """Grafana package updates select their project governance tests."""
    repo_root = Path(__file__).resolve().parents[5]

    report = build_shadow_compare(
        [
            "grafana/tooling/router-v7-bridge/package-lock.json",
            "grafana/plugins/bioetl-scenes-app/package.json",
            "grafana/plugins/bioetl-selectorshell-panel/package-lock.json",
        ],
        repo_root=repo_root,
    )

    assert set(report["selected"]) == {
        "tests/architecture/test_braces_backport.py",
        "tests/architecture/test_circleci_migration_contract.py",
        "tests/architecture/test_dashboard_scenes_contract.py",
        "tests/architecture/test_residual_osv_9853.py",
    }


def test_n1_evidence_paths_have_shadow_compare_routes() -> None:
    """Nightly, docs, and the gap archive must not fail closed as unmapped."""
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [
            ".github/workflows/nightly.yml",
            "CHANGELOG.md",
            "configs/quality/scripts_lifecycle_registry.json",
            "docs/04-reference/github-actions-workflows.md",
            "docs/05-operations/ci-workflow-map.md",
            "docs/05-operations/runbooks/generated-artifact-drift-workflow.md",
            "reports/governance/n1-shadow-window/ledger.json",
            "reports/governance/n1-shadow-window-status.md",
            "reports/quality/flaky-test-burndown-review.json",
            "reports/quality/test-governance-current.json",
        ],
        repo_root=root,
    )
    assert report["activation"] == "not_applied"
    assert report["selected_count"] >= 1
    assert (
        "tests/unit/scripts/engineering/ci/test_nightly_shadow_archive.py"
        in report["selected"]
    )


@pytest.mark.parametrize(
    "path",
    [
        ".github/workflows/type-checking.yml",
        ".github/workflows/type-checking-cold.yml",
        "scripts/engineering/dev/run_mypy.sh",
        "scripts/engineering/dev/run_mypy.ps1",
        "scripts/engineering/dev/zed_mypy.py",
        "configs/quality/github_required_checks.yaml",
    ],
)
def test_shadow_compare_routes_strict_mypy_scope_contract(path: str) -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare([path], repo_root=root)
    expected = ["tests/architecture/test_mypy_target_contract.py"]
    if path in {
        ".github/workflows/type-checking.yml",
        ".github/workflows/type-checking-cold.yml",
    }:
        expected.insert(0, "tests/architecture/test_github_actions_runtime_policy.py")
    if path == "scripts/engineering/dev/zed_mypy.py":
        expected.extend(["tests/unit/scripts", "tests/unit/repo_backed/scripts"])
    assert report["selected"] == expected


@pytest.mark.parametrize(
    "name", ["SUMMARY.md", "chembl_data.json", "uniprot_headers.txt"]
)
def test_shadow_compare_routes_provider_parity_evidence(name: str) -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare([f"reports/evidence/12461/{name}"], repo_root=root)
    assert report["selected"] == [
        "tests/architecture/test_provider_contract_interoperability_governance.py",
        "tests/contract/test_provider_contract_snapshot_registry.py",
    ]


def test_shadow_compare_routes_qm07_report_to_isolation_contracts() -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        ["reports/engineering/qm_07_report.md"], repo_root=root
    )
    assert set(report["selected"]) == {
        "tests/architecture/qm_07/test_qm07_cold_imports_isolated.py",
        "tests/architecture/qm_07/test_gate_evaluators.py",
        "tests/architecture/qm_07/test_distribution_isolation.py",
        "tests/architecture/qm_07/test_qm07_cold_imports.py",
    }


@pytest.mark.parametrize(
    "path",
    (
        "docs/00-project/RULES.md",
        "docs/05-operations/runbooks/stale-lock.md",
    ),
)
def test_shadow_compare_routes_incident_operator_docs(path: str) -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare([path], repo_root=root)
    assert report["selected"] == [
        "tests/unit/grafana/test_incident_runbook_alert_semantics.py"
    ]


@pytest.mark.parametrize(
    "path",
    (
        "reports/audit-runs/20261026-p17-003-external-callers.md",
        "reports/audit-runs/20261026-p17-003-external-callers/evidence.json",
    ),
)
def test_shadow_compare_routes_p17_003_external_caller_report(path: str) -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare([path], repo_root=root)
    assert report["covers_full_suite"] is False
    assert report["selected"] == [
        "tests/unit/scripts/ci/test_check_reusable_workflow_pins.py",
        "tests/architecture/test_github_actions_runtime_policy.py",
    ]


def test_shadow_compare_routes_issue_12485_evidence_paths() -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [
            "reports/evidence/12485/criterion_to_evidence.md",
            "reports/ledger12457_handoff.json",
        ],
        repo_root=root,
    )
    assert report["covers_full_suite"] is False
    assert report["selected"] == [
        "tests/architecture/test_config_topology_docs_drift.py",
        "tests/unit/application/composite/checkpoint/test_checkpoint_runtime.py",
        "tests/unit/domain/control_plane/test_run_ledger_replay.py",
    ]
    with pytest.raises(
        ValueError,
        match=r"unmapped paths: reports/evidence/12485/unmapped-evidence.md",
    ):
        build_shadow_compare(
            ["reports/evidence/12485/unmapped-evidence.md"], repo_root=root
        )


def test_shadow_compare_routes_low_coverage_revalidation_junit() -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        ["reports/quality/low-coverage-6045-revalidation.xml"],
        repo_root=root,
    )
    assert report["covers_full_suite"] is False
    assert report["selected"] == [
        "tests/unit/scripts/qa/test_refresh_governance_artifacts.py"
    ]


def test_shadow_compare_routes_security_suppression_registry() -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        ["configs/quality/security_suppression_registry.yaml"],
        repo_root=root,
    )
    assert report["covers_full_suite"] is False
    assert report["selected"] == [
        "tests/architecture/test_security_suppression_registry.py",
    ]


def test_shadow_compare_routes_app002_port_map_to_port_contracts() -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        ["reports/engineering/app-002-port-map/report.md"], repo_root=root
    )
    assert report["covers_full_suite"] is False
    assert report["selected"] == [
        "tests/architecture/test_port_contracts.py",
        "tests/architecture/test_application_services_cross_subdomain_imports.py",
        "tests/unit/application/ports/test_application_ports_no_factory_aliases.py",
    ]


@pytest.mark.parametrize(
    "path",
    (
        "reports/app-001-audit.md",
        "reports/audit/AUDIT-20261022-APP-001-Cancellation.md",
    ),
)
def test_shadow_compare_routes_app001_audit_to_cancellation_contracts(
    path: str,
) -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare([path], repo_root=root)
    assert report["covers_full_suite"] is False
    assert set(report["selected"]) == {
        "tests/unit/application/core/test_batch_execution_lifecycle.py",
        "tests/unit/application/core/test_derived_scan_budget.py",
        "tests/unit/application/core/test_pipeline_services.py",
        "tests/unit/application/core/test_health_aggregator.py",
        "tests/unit/application/core/test_heartbeat.py",
        "tests/unit/application/core/test_lock_release_callback_contract.py",
        "tests/unit/application/core/test_runner.py",
        "tests/unit/application/services/test_pipeline_runner_service.py",
        "tests/unit/application/services/run_reports/test_composite_report.py",
    }


def test_shadow_compare_routes_silver_filter_inventory_baseline() -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [
            "docs/filters/inventory-baseline.csv",
            "docs/filters/inventory-baseline.json",
            "docs/filters/inventory-baseline.md",
        ],
        repo_root=root,
    )
    assert report["covers_full_suite"] is False
    assert report["selected"] == [
        "tests/architecture/test_silver_filter_boundary_inventory.py"
    ]


def test_shadow_compare_routes_sec003_audit_to_metadata_parser() -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        ["reports/engineering/SEC-003_audit_report.md"], repo_root=root
    )
    assert report["selected"] == [
        "tests/unit/domain/services/test_composite_metadata_helpers.py"
    ]


def test_shadow_compare_routes_quality_and_runtime_documentation() -> None:
    """Debt and runtime documentation changes retain governing tests."""
    repo_root = Path(__file__).resolve().parents[5]

    report = build_shadow_compare(
        [
            "configs/quality/debt_scorecard.yaml",
            "docs/02-architecture/current-state-inventory.md",
            "docs/04-reference/environment-variables.md",
        ],
        repo_root=repo_root,
    )

    assert "tests/architecture/test_quality_debt_scorecard.py" in report["selected"]
    assert "tests/architecture/test_docker_runtime_contracts.py" in report["selected"]


def test_shadow_compare_routes_lineage_crash_evidence() -> None:
    """Lineage crash reports select the test that produced the evidence."""
    repo_root = Path(__file__).resolve().parents[5]

    report = build_shadow_compare(
        ["reports/audit-runs/12106-s6/evidence/evidence.md"],
        repo_root=repo_root,
    )

    assert report["selected"] == [
        "tests/integration/infrastructure/durability/test_crash_lineage.py"
    ]


def test_shadow_compare_routes_quality_module_move() -> None:
    """Both sides of the quality-module move keep governing test coverage."""
    repo_root = Path(__file__).resolve().parents[5]

    report = build_shadow_compare(
        [
            "src/bioetl/infrastructure/quality/scoring.py",
            "scripts/engineering/quality/scoring.py",
        ],
        repo_root=repo_root,
    )

    assert (
        "tests/architecture/test_architecture_quality_scorecard.py"
        in report["selected"]
    )


def test_shadow_compare_keeps_package_discovery_contract_narrow() -> None:
    """A package-discovery PR selects its changed contract without all tests."""
    repo_root = Path(__file__).resolve().parents[5]

    report = build_shadow_compare(
        ["pyproject.toml"],
        repo_root=repo_root,
        changed_python_dependencies=set(),
    )

    assert report["covers_full_suite"] is False
    assert report["selected"] == [
        "tests/architecture/qm_07/test_distribution_isolation.py"
    ]


def test_shadow_compare_routes_quality_move_governance_inputs() -> None:
    """Quality-move configs and documentation retain explicit governing tests."""
    repo_root = Path(__file__).resolve().parents[5]

    report = build_shadow_compare(
        [
            ".github/workflows/duplication-complexity.yml",
            "configs/quality/package_cohesion_budget.yaml",
            "configs/quality/scripts_lifecycle_registry.json",
            "configs/quality/technical_debt_audit_registry.yaml",
            "docs/02-architecture/current-state-inventory.md",
            "docs/04-reference/api/infrastructure.md",
            "reports/quality/total-tech-debt-audit-main-current.md",
        ],
        repo_root=repo_root,
    )

    assert (
        "tests/architecture/test_github_actions_runtime_policy.py" in report["selected"]
    )
    assert "tests/unit/scripts/qa/test_topology_source_binding.py" in report["selected"]
    assert "tests/architecture/test_scripts_lifecycle_registry.py" in report["selected"]
    assert (
        "tests/architecture/test_api_reference_public_facades.py" in report["selected"]
    )
    assert (
        "tests/unit/scripts/engineering/qa/test_technical_debt_audit_registry.py"
        in report["selected"]
    )


def test_shadow_compare_routes_issue_12475_physical_parity_evidence() -> None:
    """Physical parity evidence selects its storage and docs regressions."""
    repo_root = Path(__file__).resolve().parents[5]

    report = build_shadow_compare(
        ["reports/quality/issue-12475-physical-parity-evidence.md"],
        repo_root=repo_root,
    )

    assert (
        "tests/integration/infrastructure/storage/test_issue_12475_physical_parity.py"
        in report["selected"]
    )
    assert (
        "tests/architecture/test_documentation_cleanup_inventory.py"
        in report["selected"]
    )


def test_shadow_compare_rejects_mixed_diff_with_unmapped_path(
    tmp_path: Path,
) -> None:
    """One unmapped path fails the report even when another path selects tests."""
    unit_domain = tmp_path / "tests" / "unit" / "domain"
    unit_domain.mkdir(parents=True)
    (unit_domain / "test_sample.py").write_text(
        "def test_sample():\n    assert True\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unmapped paths: docs/readme.md"):
        build_shadow_compare(
            ["tests/unit/domain/test_sample.py", "docs/readme.md"],
            repo_root=tmp_path,
        )


def test_shadow_compare_marks_full_suite_for_empty_diff(tmp_path: Path) -> None:
    """An empty diff is recorded as the full suite and still stays observational."""
    (tmp_path / "tests").mkdir()

    report = build_shadow_compare([], repo_root=tmp_path)

    assert report["activation"] == "not_applied"
    assert report["covers_full_suite"] is True
    assert report["selected"] == ["tests"]


def test_shadow_compare_cli_fails_closed_on_unmapped_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An unmapped path must not produce a successful shadow report."""
    repo_root = Path(__file__).resolve().parents[5]
    assert (
        lane_main(
            [
                "shadow-compare",
                "--repo-root",
                str(repo_root),
                "--changed-file",
                "docs/readme.md",
            ]
        )
        == 1
    )
    assert "unmapped paths: docs/readme.md" in capsys.readouterr().err


def test_shadow_compare_cli_writes_canonical_json(tmp_path: Path) -> None:
    """The report file is canonical JSON and replaces the path atomically."""
    (tmp_path / "tests").mkdir()
    output = tmp_path / "reports" / "impact-shadow-compare.json"

    assert (
        lane_main(
            [
                "shadow-compare",
                "--repo-root",
                str(tmp_path),
                "--changed-file",
                " ",
                "--output",
                str(output),
            ]
        )
        == 0
    )

    payload = output.read_text(encoding="utf-8")
    assert payload.endswith("\n")
    assert json.loads(payload)["activation"] == "not_applied"
    assert list(json.loads(payload)) == [
        "activation",
        "covers_full_suite",
        "full_suite_root",
        "mode",
        "selected",
        "selected_count",
    ]
    assert not output.with_suffix(".json.tmp").exists()


def test_required_tests_gate_requires_shadow_step() -> None:
    """A required tests gate fails closed when the shadow step did not succeed."""
    failures = assert_step_outcomes(
        {"tests": {"decision": "required", "reason": "path_match"}},
        {"affected-pytest": "success", "impact-shadow-compare": "skipped"},
        owner="class-lane",
    )

    assert failures == ["tests:impact-shadow-compare=skipped"]


def test_unmapped_path_still_has_no_pytest_target(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A real unmapped path stays fail-closed and does not expand to every test."""
    repo_root = Path(__file__).resolve().parents[5]
    assert (
        lane_main(
            [
                "affected-tests",
                "--repo-root",
                str(repo_root),
                "--changed-file",
                "docs/readme.md",
            ]
        )
        == 1
    )
    assert "tests gate has no affected pytest target" in capsys.readouterr().err


def test_affected_targets_map_source_and_existing_tests(tmp_path: Path) -> None:
    """Select source-layer tests and existing test paths, excluding missing paths."""
    unit_domain = tmp_path / "tests" / "unit" / "domain"
    unit_domain.mkdir(parents=True)
    test_file = tmp_path / "tests" / "unit" / "domain" / "test_sample.py"
    test_file.write_text("def test_sample():\n    assert True\n", encoding="utf-8")
    missing = tmp_path / "tests" / "unit" / "missing_test.py"

    targets = affected_pytest_targets(
        [
            "src/bioetl/domain/sample.py",
            test_file.relative_to(tmp_path).as_posix(),
            missing.relative_to(tmp_path).as_posix(),
            "docs/readme.md",
        ],
        repo_root=tmp_path,
    )

    # The selected parent suite already executes test_sample.py exactly once.
    assert targets == ["tests/unit/domain"]


def test_affected_targets_map_integration_vcr_policy() -> None:
    """VCR policy edits select the inventory architecture test."""
    repo_root = Path(__file__).resolve().parents[5]
    assert affected_pytest_targets(
        ["configs/quality/integration_vcr_policy.yaml"],
        repo_root=repo_root,
    ) == ["tests/architecture/test_integration_vcr_policy.py"]


def test_affected_targets_map_telemetry_baseline(tmp_path: Path) -> None:
    """Telemetry edits select both baseline guards and leave other configs unmapped."""
    governance = tmp_path / "tests/architecture/test_test_telemetry_governance.py"
    governance.parent.mkdir(parents=True)
    governance.write_text(
        "def test_identity() -> None:\n    assert True\n", encoding="utf-8"
    )
    (governance.parent / "test_test_telemetry_baseline.py").write_text(
        "def test_baseline() -> None:\n    assert True\n", encoding="utf-8"
    )
    targets = affected_pytest_targets(
        [
            "configs/quality/test_telemetry_baseline.yaml",
            "docs/readme.md",
        ],
        repo_root=tmp_path,
    )
    untouched = affected_pytest_targets(
        ["configs/quality/unregistered-config.yaml"],
        repo_root=tmp_path,
    )

    assert targets == [
        "tests/architecture/test_test_telemetry_baseline.py",
        "tests/architecture/test_test_telemetry_governance.py",
    ]
    assert untouched == []


def test_affected_targets_map_test_governance_audit_config() -> None:
    """Test-governance config changes select their owning report checks."""
    repo_root = Path(__file__).resolve().parents[5]
    assert affected_pytest_targets(
        ["configs/quality/test_governance_audit.yaml"],
        repo_root=repo_root,
    ) == [
        "tests/architecture/test_test_governance_audit.py",
        "tests/architecture/test_tech_debt_issues_5514_5515_governance.py",
    ]


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


def test_affected_targets_map_memory_source_without_test_diff() -> None:
    """A chunking-only PR must select its real RAG regression suite."""
    repo_root = Path(__file__).resolve().parents[5]
    targets = affected_pytest_targets(
        ["src/memory/rag/chunking.py", "src/memory/rag/chunking.py"],
        repo_root=repo_root,
    )

    assert targets == ["tests/unit/memory/test_rag_indexing.py"]
    assert all((repo_root / target).is_file() for target in targets)


def test_affected_targets_fail_closed_without_memory_test(tmp_path: Path) -> None:
    """A mapping never turns an absent test into a passing target."""
    with pytest.raises(ValueError, match="Missing mandatory mapped test targets"):
        affected_pytest_targets(["src/memory/rag/chunking.py"], repo_root=tmp_path)


def test_affected_targets_preserve_docs_workflow_specialized_contracts() -> None:
    """The general workflow map must not erase the docs-specific contracts."""
    repo_root = Path(__file__).resolve().parents[5]
    assert affected_pytest_targets(
        [".github/workflows/docs.yml"], repo_root=repo_root
    ) == [
        "tests/architecture/test_docs_governance_workflow.py",
        "tests/architecture/test_diagram_nightly_workflow.py",
        "tests/architecture/test_github_actions_runtime_policy.py",
    ]


def test_affected_targets_map_makefile_benchmark_contract() -> None:
    """Makefile edits select the benchmark-target contract, not an empty lane."""
    repo_root = Path(__file__).resolve().parents[5]
    assert affected_pytest_targets(["Makefile"], repo_root=repo_root) == [
        "tests/unit/repo_backed/scripts/engineering/ci/test_makefile_benchmark_target.py",
    ]


def test_affected_targets_map_root_npm_only_and_deduplicate() -> None:
    """Manifest-only tooling updates execute their existing runtime contract."""
    repo_root = Path(__file__).resolve().parents[5]
    assert affected_pytest_targets(
        ["package.json", "package-lock.json", "package.json"], repo_root=repo_root
    ) == [
        "tests/architecture/test_observability_dashboard_tooling.py",
        "tests/unit/repo_backed/scripts/ai/test_npm_runtime_contract.py",
    ]


def test_python_dependency_diff_must_be_verified(tmp_path: Path) -> None:
    """No fixed unrelated list can qualify a Python dependency gate."""
    with pytest.raises(ValueError, match="verified dependency diff"):
        affected_pytest_targets(["uv.lock"], repo_root=tmp_path)


@pytest.mark.parametrize(
    "changed_file", ["package.json", "package-lock.json", "pyproject.toml", "uv.lock"]
)
def test_root_npm_lane_fails_when_target_is_missing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], changed_file: str
) -> None:
    """An absent mapped contract cannot satisfy required affected-tests."""
    with pytest.raises(ValueError):
        affected_pytest_targets([changed_file], repo_root=tmp_path)
    assert (
        lane_main(
            [
                "affected-tests",
                "--repo-root",
                str(tmp_path),
                "--changed-file",
                changed_file,
            ]
        )
        == 1
    )
    assert "tests gate selection failed" in capsys.readouterr().err


def test_affected_targets_preserve_bioetl_and_scripts_routes(tmp_path: Path) -> None:
    """Memory routing keeps the existing source and script selection."""
    (tmp_path / "tests/unit/domain").mkdir(parents=True)
    script_test = tmp_path / "tests/unit/scripts/engineering/ci/test_tool.py"
    script_test.parent.mkdir(parents=True)
    script_test.write_text("def test_tool():\n    assert True\n", encoding="utf-8")

    targets = affected_pytest_targets(
        ["src/bioetl/domain/sample.py", "scripts/engineering/ci/tool.py"],
        repo_root=tmp_path,
    )

    assert targets == [
        "tests/unit/domain",
        "tests/unit/scripts/engineering/ci/test_tool.py",
    ]


def test_build_rejects_unknown_decision() -> None:
    """Reject gate decisions outside the coordinator decision vocabulary."""
    with pytest.raises(ValueError, match="unknown decision"):
        build_results(
            {"tests": {"decision": "maybe"}},
            {},
            head_sha=HEAD,
        )


@pytest.mark.parametrize("missing_count", [0, 1, 2])
def test_partial_mapped_targets_fail_lane(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    missing_count: int,
) -> None:
    """Reject partial mappings before printing targets for the caller to run."""
    from scripts.engineering.ci import pr_lane_results as lane

    mapped = ("tests/unit/test_one.py", "tests/unit/test_two.py")
    monkeypatch.setitem(lane.AFFECTED_TESTS_BY_PATH, "fixture/source.py", mapped)
    for target in mapped[: 2 - missing_count]:
        path = tmp_path / target
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("def test_contract(): pass\n", encoding="utf-8")
    result = lane_main(
        [
            "affected-tests",
            "--repo-root",
            str(tmp_path),
            "--changed-file",
            "fixture/source.py",
        ]
    )
    captured = capsys.readouterr()
    if missing_count:
        assert result == 1
        assert not captured.out
        for target in mapped[2 - missing_count :]:
            assert target in captured.err
    else:
        assert result == 0
        assert captured.out.splitlines() == list(mapped)


def test_mcp_check_source_routes_both_mandatory_contract_suites(tmp_path: Path) -> None:
    from scripts.engineering.ci.pr_lane_results import (
        affected_pytest_targets,
        NPM_RUNTIME_TEST,
    )

    mcp_target = "tests/unit/repo_backed/scripts/ai/mcp/test_mcp_wrapper_contracts.py"
    for name in (NPM_RUNTIME_TEST, mcp_target):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    assert affected_pytest_targets(["scripts/ai/mcp/check.sh"], repo_root=tmp_path) == [
        NPM_RUNTIME_TEST,
        mcp_target,
    ]
    (tmp_path / mcp_target).unlink()
    with pytest.raises(ValueError, match="Missing mandatory mapped test targets"):
        affected_pytest_targets(["scripts/ai/mcp/check.sh"], repo_root=tmp_path)


def test_complete_suite_removes_nested_duplicates_after_required_validation(
    tmp_path: Path,
) -> None:
    from scripts.engineering.ci.pr_lane_results import affected_pytest_targets

    rag = "tests/unit/memory/test_rag_indexing.py"
    path = tmp_path / rag
    path.parent.mkdir(parents=True)
    path.touch()
    (tmp_path / "uv.lock").write_text("version = 1\n", encoding="utf-8")
    changed = ["uv.lock", "src/memory/rag/chunking.py", rag]
    assert affected_pytest_targets(
        changed, repo_root=tmp_path, changed_python_dependencies={"pytest"}
    ) == ["tests"]
    path.unlink()
    with pytest.raises(ValueError, match="Missing mandatory mapped test targets"):
        affected_pytest_targets(
            changed, repo_root=tmp_path, changed_python_dependencies={"pytest"}
        )


def test_router_executes_lane_results_as_importable_module(capsys):
    """Verify router executes lane results as importable module."""
    from scripts.engineering.ci.__main__ import main

    assert main(["pr-lane-results", "--help"]) == 0
    assert "affected-tests" in capsys.readouterr().out


def test_benchmark_and_governance_artifacts_have_impact_routes() -> None:
    """Durable evidence and coupled snapshots select their governing tests."""
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [
            ".gitignore",
            "configs/quality/generated_artifact_routing.yaml",
            "configs/quality/generated_artifact_tests.json",
            "configs/quality/test_skip_inventory.yaml",
            "Dockerfile.bioetl",
            "docs/reports/generated/documentation-cleanup-inventory.json",
            "docs/reports/generated/documentation-cleanup-inventory.md",
            "reports/performance/benchmark-summary.json",
            "reports/quality/external-resource-inventory.md",
            "reports/security/blocker-CVE-out-of-scope.md",
            (
                "reports/performance/evidence/deadbeef/raw/"
                "benchmark-validation-manifest.json"
            ),
            "reports/quality/flaky-test-burndown-review.json",
            "reports/quality/test-governance-current.json",
        ],
        repo_root=repo_root,
    )

    assert report["activation"] == "not_applied"
    assert report["covers_full_suite"] is False
    selected = set(report["selected"])
    baseline = {
        "tests/architecture/test_documentation_cleanup_inventory.py",
        "tests/architecture/test_docker_runtime_contracts.py",
        "tests/architecture/test_generated_artifact_routing.py",
        "tests/architecture/test_gitignore_secret_and_agents_policy.py",
        "tests/architecture/test_tech_debt_issues_5559_5563_closeout.py",
        "tests/architecture/test_test_skip_inventory.py",
        "tests/architecture/test_tech_debt_issues_5514_5515_governance.py",
        "tests/architecture/test_test_governance_audit.py",
        "tests/unit/repo_backed/scripts/qa/test_validate_benchmark_evidence_repo.py",
        "tests/unit/scripts/engineering/ci/test_pr_lane_results.py",
    }
    registry = json.loads(
        (repo_root / "configs/quality/generated_artifact_tests.json").read_text(
            encoding="utf-8"
        )
    )
    generated_owners = {
        record["node"].partition("::")[0]
        for record in registry["tests"]
        if "reports/quality/test-governance-current.json" in record["artifacts"]
    }
    assert baseline <= selected
    assert generated_owners <= selected


def test_base_checkout_aggregation_uses_existing_module_entrypoint():
    """Verify base checkout aggregation uses existing module entrypoint."""
    import yaml

    root = Path(__file__).resolve().parents[5]
    workflow = yaml.safe_load(
        (root / ".github/workflows/pr-required.yml").read_text(encoding="utf-8")
    )
    steps = workflow["jobs"]["pr-gate-complete"]["steps"]
    build = next(
        step["run"] for step in steps if "pr_lane_results build" in step.get("run", "")
    )
    assert "python -m scripts.engineering.ci.pr_lane_results build" in build


def test_record_steps_uses_bounded_outcomes_instead_of_all_step_outputs() -> None:
    """Keep large action outputs out of the recorder process environment."""
    import re
    import yaml

    root = Path(__file__).resolve().parents[5]
    workflow_text = (root / ".github/workflows/pr-required.yml").read_text(
        encoding="utf-8"
    )
    assert "toJson(steps)" not in workflow_text

    workflow = yaml.safe_load(workflow_text)
    for job_id, owner in (
        ("fast-governance", "fast-governance"),
        ("class-lane", "class-lane"),
    ):
        record = next(
            step
            for step in workflow["jobs"][job_id]["steps"]
            if step.get("name") == "Record required step outcomes"
        )
        serialized = set(re.findall(r"steps\.([a-z0-9-]+)\.outcome", record["run"]))
        required = {
            step_id for step_ids in OWNER_STEPS[owner].values() for step_id in step_ids
        }
        audited = (
            {"zizmor", "dependency-review"} if owner == "fast-governance" else set()
        )
        assert serialized == required | audited


def test_assert_steps_malformed_outcomes() -> None:
    """Simulate a malformed outcome payload that includes strange formatting."""
    failures = assert_step_outcomes(
        {"type-checking": {"decision": "required", "reason": "path_match"}},
        {
            "mypy": "",  # Missing outcome
            "newtype-protocol": "success",
            "any-usage": "success",
        },
        owner="class-lane",
    )

    # Empty string outcome defaults to 'missing' string representation in assert_step_outcomes
    assert failures == ["type-checking:mypy=missing"]


def test_assert_steps_reports_audited_action_failure() -> None:
    """A failing audited action remains visible outside gate-owned steps."""
    failures = assert_step_outcomes(
        {},
        {"zizmor": "failure", "dependency-review": "skipped"},
        owner="fast-governance",
    )

    assert failures == ["step:zizmor=failure"]


def test_generated_artifact_sibling_uses_canonical_test_registry(
    tmp_path: Path,
) -> None:
    """Route a generated sibling through its registered artifact test."""
    test_path = "tests/architecture/test_generated_report.py"
    target = tmp_path / test_path
    target.parent.mkdir(parents=True)
    target.write_text("def test_report():\n    assert True\n", encoding="utf-8")
    registry = tmp_path / "configs/quality/generated_artifact_tests.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "tests": [
                    {
                        "node": f"{test_path}::test_report",
                        "artifacts": ["reports/quality/report.json"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (registry.parent / "generated_artifact_routing.yaml").write_text(
        "routes:\n"
        "  - id: report\n"
        "    outputs:\n"
        "      - reports/quality/report.json\n"
        "      - reports/quality/report.md\n",
        encoding="utf-8",
    )

    report = build_shadow_compare(
        ["reports/quality/report.md"],
        repo_root=tmp_path,
    )

    assert report["selected"] == [test_path]


def test_generated_artifact_route_unions_direct_and_sibling_tests(
    tmp_path: Path,
) -> None:
    """A direct artifact match must not hide tests owned by its sibling."""
    json_test = "tests/architecture/test_generated_json.py"
    markdown_test = "tests/architecture/test_generated_markdown.py"
    for test_path in (json_test, markdown_test):
        target = tmp_path / test_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("def test_report():\n    assert True\n", encoding="utf-8")
    registry = tmp_path / "configs/quality/generated_artifact_tests.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "tests": [
                    {
                        "node": f"{json_test}::test_report",
                        "artifacts": ["reports/quality/report.json"],
                    },
                    {
                        "node": f"{markdown_test}::test_report",
                        "artifacts": ["reports/quality/report.md"],
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    (registry.parent / "generated_artifact_routing.yaml").write_text(
        "routes:\n"
        "  - id: report\n"
        "    outputs:\n"
        "      - reports/quality/report.json\n"
        "      - reports/quality/report.md\n",
        encoding="utf-8",
    )

    report = build_shadow_compare(
        ["reports/quality/report.json"],
        repo_root=tmp_path,
    )

    assert report["selected"] == [json_test, markdown_test]


def test_static_mapping_unions_generated_registry_tests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A static path mapping must not suppress generated-registry owners."""
    from scripts.engineering.ci import pr_lane_results as lane

    artifact = "reports/quality/report.json"
    static_test = "tests/architecture/test_static_owner.py"
    generated_test = "tests/architecture/test_generated_owner.py"
    for test_path in (static_test, generated_test):
        target = tmp_path / test_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("def test_report():\n    assert True\n", encoding="utf-8")
    monkeypatch.setitem(lane.AFFECTED_TESTS_BY_PATH, artifact, (static_test,))
    registry = tmp_path / "configs/quality/generated_artifact_tests.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "tests": [
                    {
                        "node": f"{generated_test}::test_report",
                        "artifacts": [artifact],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    report = build_shadow_compare([artifact], repo_root=tmp_path)

    assert report["selected"] == [static_test, generated_test]


def test_generated_artifact_directory_output_routes_descendants(
    tmp_path: Path,
) -> None:
    """A tracked output directory owns generated files below it."""
    test_path = "tests/architecture/test_generated_directory.py"
    target = tmp_path / test_path
    target.parent.mkdir(parents=True)
    target.write_text("def test_report():\n    assert True\n", encoding="utf-8")
    registry = tmp_path / "configs/quality/generated_artifact_tests.json"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "tests": [
                    {
                        "node": f"{test_path}::test_report",
                        "artifacts": ["docs/generated/"],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    (registry.parent / "generated_artifact_routing.yaml").write_text(
        "routes:\n  - id: docs\n    outputs:\n      - docs/generated/\n",
        encoding="utf-8",
    )

    report = build_shadow_compare(
        ["docs/generated/nested/report.json"],
        repo_root=tmp_path,
    )

    assert report["selected"] == [test_path]


def _reject_collection(
    targets: Sequence[str], *, marker: str | None = None
) -> set[str]:
    raise AssertionError((targets, marker))


def test_subtraction_keeps_disjoint_targets_without_collection() -> None:
    """A target outside the fixed lane is not collected or rewritten."""
    plan = plan_affected_subtraction(
        ["tests/unit/test_sample.py"],
        ["tests/architecture"],
        collect_nodeids=_reject_collection,
    )
    assert plan.execution_targets == ("tests/unit/test_sample.py",)
    assert plan.ignore_paths == ()
    assert plan.intersection == ()


def test_subtraction_drops_fixed_lane_files_and_reports_nodeids() -> None:
    """Selectors already owned by the fixed lane are omitted, not re-run."""
    seen: list[tuple[tuple[str, ...], str | None]] = []

    def collect(targets: Sequence[str], *, marker: str | None = None) -> set[str]:
        seen.append((tuple(targets), marker))
        return {f"{targets[0]}::test_covered"}

    plan = plan_affected_subtraction(
        ["tests/unit/test_sample.py", "tests/architecture/test_ci.py"],
        ["tests/architecture"],
        collect_nodeids=collect,
    )
    assert plan.execution_targets == ("tests/unit/test_sample.py",)
    assert plan.ignore_paths == ()
    assert plan.intersection == ("tests/architecture/test_ci.py::test_covered",)
    assert seen == [
        (
            ("tests/architecture/test_ci.py",),
            "not slow and not benchmark and not memory",
        ),
        (("tests/architecture/test_ci.py",), None),
    ]


def test_subtraction_ignores_fixed_root_when_parent_is_selected() -> None:
    """The full suite stays one target and ignores the fixed lane."""

    def collect(targets: Sequence[str], *, marker: str | None = None) -> set[str]:
        assert tuple(targets) == ("tests/architecture",)
        assert marker in (None, "not slow and not benchmark and not memory")
        return {
            "tests/architecture/test_ci.py::test_one",
            "tests/architecture/test_ci.py::test_two",
        }

    plan = plan_affected_subtraction(
        ["tests"],
        ["tests/architecture"],
        collect_nodeids=collect,
    )
    assert plan.execution_targets == ("tests",)
    assert plan.ignore_paths == ("tests/architecture",)
    assert plan.intersection == (
        "tests/architecture/test_ci.py::test_one",
        "tests/architecture/test_ci.py::test_two",
    )


def test_subtraction_keeps_tests_the_fixed_lane_skips() -> None:
    """Slow architecture tests stay in the affected run."""

    def collect(targets: Sequence[str], *, marker: str | None = None) -> set[str]:
        assert tuple(targets) == ("tests/architecture/test_ci.py",)
        if marker:
            return {"tests/architecture/test_ci.py::test_fast"}
        return {
            "tests/architecture/test_ci.py::test_fast",
            "tests/architecture/test_ci.py::test_slow",
        }

    plan = plan_affected_subtraction(
        ["tests/architecture/test_ci.py"],
        ["tests/architecture"],
        collect_nodeids=collect,
    )
    assert plan.execution_targets == ("tests/architecture/test_ci.py::test_slow",)
    assert plan.ignore_paths == ()
    assert plan.intersection == ("tests/architecture/test_ci.py::test_fast",)


def test_subtraction_fails_closed_on_empty_selection() -> None:
    """An empty affected file is a broken selector, not an empty success."""
    with pytest.raises(ValueError, match="no affected pytest target"):
        plan_affected_subtraction(
            [],
            ["tests/architecture"],
            collect_nodeids=_reject_collection,
        )


def test_subtract_command_writes_plan_and_intersection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The CLI records covered nodeids and the ignore used at execution time."""
    from scripts.engineering.ci import pr_lane_results as lane

    affected = tmp_path / "affected.txt"
    affected.write_text("tests\n", encoding="utf-8")
    output = tmp_path / "deduped.txt"
    ignore = tmp_path / "ignores.txt"

    def collect(
        root: Path, targets: Sequence[str], *, marker: str | None = None
    ) -> set[str]:
        assert root == tmp_path
        assert tuple(targets) == ("tests/architecture",)
        assert marker in (None, "not slow and not benchmark and not memory")
        return {"tests/architecture/test_ci.py::test_one"}

    monkeypatch.setattr(lane, "_collect_nodeids", collect)
    assert (
        lane_main(
            [
                "subtract-affected",
                "--repo-root",
                str(tmp_path),
                "--fixed-targets",
                "tests/architecture",
                "--affected-file",
                str(affected),
                "--output",
                str(output),
                "--ignore-file",
                str(ignore),
            ]
        )
        == 0
    )
    assert output.read_text(encoding="utf-8") == "tests\n"
    assert ignore.read_text(encoding="utf-8") == "tests/architecture\n"
    captured = capsys.readouterr()
    assert "tests/architecture/test_ci.py::test_one" in captured.err
    assert "fixed-lane ignores: tests/architecture" in captured.err


def test_subtract_command_fail_closed_does_not_write_targets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A broken selector must not leave a runnable target file behind."""
    from scripts.engineering.ci import pr_lane_results as lane

    affected = tmp_path / "affected.txt"
    affected.write_text("tests/architecture/test_missing.py\n", encoding="utf-8")
    output = tmp_path / "deduped.txt"

    def collect(
        _root: Path, _targets: Sequence[str], *, marker: str | None = None
    ) -> set[str]:
        raise ValueError(f"pytest collection failed (4) {marker}")

    monkeypatch.setattr(lane, "_collect_nodeids", collect)
    assert (
        lane_main(
            [
                "subtract-affected",
                "--repo-root",
                str(tmp_path),
                "--fixed-targets",
                "tests/architecture",
                "--affected-file",
                str(affected),
                "--output",
                str(output),
                "--ignore-file",
                str(tmp_path / "ignores.txt"),
            ]
        )
        == 1
    )
    assert not output.exists()
    assert not (tmp_path / "ignores.txt").exists()


def test_subtract_command_writes_empty_plan_when_lane_covers_all(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Full overlap is a successful skip, not a failed tests gate."""
    from scripts.engineering.ci import pr_lane_results as lane

    affected = tmp_path / "affected.txt"
    affected.write_text("tests/architecture/test_ci.py\n", encoding="utf-8")
    output = tmp_path / "deduped.txt"
    ignore = tmp_path / "ignores.txt"

    def collect(
        _root: Path, targets: Sequence[str], *, marker: str | None = None
    ) -> set[str]:
        assert marker in (None, "not slow and not benchmark and not memory")
        return {f"{targets[0]}::test_covered"}

    monkeypatch.setattr(lane, "_collect_nodeids", collect)
    assert (
        lane_main(
            [
                "subtract-affected",
                "--repo-root",
                str(tmp_path),
                "--fixed-targets",
                "tests/architecture",
                "--affected-file",
                str(affected),
                "--output",
                str(output),
                "--ignore-file",
                str(ignore),
            ]
        )
        == 0
    )
    assert output.read_text(encoding="utf-8") == ""
    assert ignore.read_text(encoding="utf-8") == ""


def test_collect_nodeids_parses_pytest_collection(tmp_path: Path) -> None:
    """Collection keeps real nodeids and rejects a missing selector."""
    from scripts.engineering.ci.pr_lane_results import _collect_nodeids

    test_file = tmp_path / "tests" / "test_sample.py"
    test_file.parent.mkdir()
    test_file.write_text("def test_one():\n    assert True\n", encoding="utf-8")
    assert _collect_nodeids(tmp_path, ["tests/test_sample.py"]) == {
        "tests/test_sample.py::test_one"
    }
    with pytest.raises(ValueError, match="pytest collection failed"):
        _collect_nodeids(tmp_path, ["tests/missing.py"])


@pytest.mark.parametrize(
    "changed_file",
    [
        "configs/quality/external_resource_inventory.json",
        *[
            f"configs/quality/external_resource_inventory/part-{index:02}.json"
            for index in range(1, 6)
        ],
        "reports/quality/external-resource-inventory.md",
        "scripts/engineering/qa/README.md",
    ],
)
def test_resource_inventory_files_select_integrity_controls(changed_file: str) -> None:
    """Every inventory input and projection retains its owning integrity suite."""
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare([changed_file], repo_root=root)
    assert (
        "tests/unit/scripts/engineering/qa/test_external_resource_inventory.py"
        in report["selected"]
    )
    catalog_test = "tests/architecture/test_external_resource_inventory_catalog.py"
    assert catalog_test in report["selected"]
    assert (root / catalog_test).is_file()
    assert report["activation"] == "not_applied"
