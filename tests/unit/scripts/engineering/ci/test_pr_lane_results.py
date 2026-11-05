"""Unit tests for coordinator job-result mapping."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
from scripts.engineering.ci.pr_lane_results import (
    affected_pytest_targets,
    assert_step_outcomes,
    build_results,
    build_shadow_compare,
    main as lane_main,
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


def test_shadow_compare_routes_12380_acceptance_report() -> None:
    """Issue 12380 acceptance markdown is a docs/report artifact, not code."""
    repo_root = Path(__file__).resolve().parents[5]

    report = build_shadow_compare(
        ["reports/engineering/12380_acceptance_report.md"],
        repo_root=repo_root,
    )

    assert report["selected"] == [
        "tests/architecture/test_documentation_cleanup_inventory.py"
    ]
    assert report["covers_full_suite"] is False


@pytest.mark.parametrize(
    "path",
    (
        "reports/audit/pack-v2.1/P02-ddd-domain.md",
        "reports/audit/pack-v2.1/P02-invariant-runs.log",
        "reports/audit/pack-v2.1/domain-pylint-duplicate-code-scan.log",
        "reports/audit/pack-v2.1/domain-vulture-dead-code-scan.log",
        "reports/audit/pack-v2.1/P05-interfaces-contracts.md",
    ),
)
def test_shadow_compare_routes_pack_v21_stage_audit_reports(path: str) -> None:
    """pack-v2.1 stage handoffs stay on the cleanup-inventory contract."""
    repo_root = Path(__file__).resolve().parents[5]

    report = build_shadow_compare([path], repo_root=repo_root)

    assert report["selected"] == [
        "tests/architecture/test_documentation_cleanup_inventory.py"
    ]
    assert report["covers_full_suite"] is False


@pytest.mark.parametrize("path", [".gitleaksignore", ".gitleaks.toml"])
def test_shadow_compare_routes_secret_scanner_policy(path: str) -> None:
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare([path], repo_root=repo_root)
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


def test_shadow_compare_routes_run_report_contracts_and_docs() -> None:
    """Run-report contracts, goldens, and operator docs select contract tests."""
    repo_root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [
            "configs/contracts/reports/run_evidence_location.v1.json",
            "tests/fixtures/reports/run_evidence_location_golden.json",
            "docs/04-reference/reports/run-reports.md",
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
            "grafana/plugins/eslint-shared-config.mjs",
        ],
        repo_root=repo_root,
    )

    assert set(report["selected"]) == {
        "tests/architecture/test_braces_backport.py",
        "tests/architecture/test_circleci_migration_contract.py",
        "tests/architecture/test_dashboard_scenes_contract.py",
        "tests/architecture/test_residual_osv_9853.py",
    }


def test_shadow_compare_routes_monitoring_and_docker_security_docs() -> None:
    """Monitoring configuration and its security runbook select owner tests."""
    repo_root = Path(__file__).resolve().parents[5]
    for changed_file in (
        "docker-compose.monitoring.yml",
        "docs/05-operations/runbooks/docker-security-baseline.md",
    ):
        route = build_shadow_compare([changed_file], repo_root=repo_root)
        assert (
            "tests/architecture/test_docker_runtime_contracts.py" in route["selected"]
        )

    report = build_shadow_compare(
        [
            "docker-compose.monitoring.yml",
            "docs/05-operations/runbooks/docker-security-baseline.md",
        ],
        repo_root=repo_root,
    )

    assert set(report["selected"]) == {
        "tests/architecture/test_docker_runtime_contracts.py",
        "tests/integration/test_grafana_datasource_provisioning.py",
        "tests/integration/test_dashboard_operator_readability.py",
        "tests/architecture/test_documentation_cleanup_inventory.py",
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


def test_shadow_compare_routes_run_manifest_inspection_runbook() -> None:
    """RF-008 runbook edits must map to verify_report_bind + deployed replay tests."""
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        ["docs/05-operations/runbooks/run-manifest-inspection.md"],
        repo_root=root,
    )
    assert report["selected"] == [
        "tests/unit/scripts/ops/docker/test_verify_report_bind.py",
        "tests/integration/test_deployed_replay_readiness.py",
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


def test_shadow_compare_routes_test_health_summary_to_freshness_owners() -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        ["docs/reports/evidence/project-test-health/SUMMARY.md"], repo_root=root
    )
    assert report["covers_full_suite"] is False
    assert set(report["selected"]) == {
        "tests/architecture/test_governance_freshness_protocol.py",
        "tests/architecture/test_runtime_agent_docs_drift.py",
        "tests/unit/scripts/docs/test_check_drift_evidence_age.py",
    }
    with pytest.raises(ValueError, match="unmapped paths"):
        build_shadow_compare(
            ["docs/reports/evidence/project-test-health/unowned.md"], repo_root=root
        )


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


def test_shadow_compare_routes_root_vulture_whitelist_and_allowlist() -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare(
        [".github/root-allowlist.txt", ".vulture_whitelist.py"],
        repo_root=root,
    )
    assert report["covers_full_suite"] is False
    assert set(report["selected"]) == {
        "tests/architecture/test_layer_dependencies.py",
        "tests/architecture/test_root_hygiene_review_registry.py",
        "tests/architecture/test_tech_debt_issues_5847_5852_closeout.py",
    }


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


def test_shadow_compare_routes_current_policy_and_test_health_evidence() -> None:
    repo_root = Path(__file__).resolve().parents[5]
    changed_paths = [
        "configs/quality/layered_suffix_policy.yaml",
        "docs/reports/evidence/project-test-health/SUMMARY.md",
        "docs/reports/evidence/project-test-health/metadata.yaml",
        "docs/reports/evidence/project-test-health/shard_registry.yaml",
    ]

    for path in changed_paths:
        report = build_shadow_compare([path], repo_root=repo_root)
        assert report["selected_count"] > 0


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

    catalog_and_requalify_tests = {
        "tests/architecture/test_external_resource_inventory_catalog.py",
        "tests/unit/scripts/engineering/qa/test_requalify_external_resource_inventory.py",
    }
    new_inputs = {
        "configs/quality/external_resource_inventory/part-06.json": {
            "tests/architecture/test_external_resource_inventory_catalog.py",
            "tests/unit/scripts/engineering/qa/test_external_resource_inventory.py",
        },
        "configs/quality/external_resource_inventory_qm08_review.json": (
            catalog_and_requalify_tests
        ),
        "configs/quality/external_resource_inventory_qm09_review.json": (
            catalog_and_requalify_tests
        ),
        "configs/quality/external_resource_inventory_pr12688_rf002_review.json": (
            catalog_and_requalify_tests
        ),
        "configs/quality/external_resource_inventory_pr12728_main_merge_12737_review.json": (
            catalog_and_requalify_tests
        ),
        "configs/quality/external_resource_inventory_pr12728_mypy_types_review.json": (
            catalog_and_requalify_tests
        ),
        "configs/quality/external_resource_inventory_pr12748_status_cache_review.json": (
            catalog_and_requalify_tests
        ),
        "configs/quality/external_resource_inventory_pr12751_main_merge_review.json": (
            catalog_and_requalify_tests
        ),
        "configs/quality/external_resource_inventory_pr12755_main_merge_review.json": (
            catalog_and_requalify_tests
        ),
        "configs/quality/external_resource_inventory_pr12730_rf001_004_review.json": (
            catalog_and_requalify_tests
        ),
        "configs/quality/quality_move_qm09_reference_decisions.json": {
            "tests/unit/scripts/engineering/qa/test_verify_quality_move.py",
        },
        "reports/quality/quality-move-qm08/publication-provenance.json": {
            "tests/unit/scripts/ci/test_test_telemetry_provenance.py",
            "tests/architecture/test_external_resource_inventory_catalog.py",
        },
        "docker-compose.monitoring.yml": {
            "tests/architecture/test_docker_runtime_contracts.py",
            "tests/integration/test_grafana_datasource_provisioning.py",
        },
    }
    for path, owning_tests in new_inputs.items():
        selection = build_shadow_compare([path], repo_root=repo_root)
        assert owning_tests <= set(selection["selected"]), path
        assert selection["covers_full_suite"] is False

    report = build_shadow_compare(
        [
            ".github/workflows/duplication-complexity.yml",
            "configs/quality/package_cohesion_budget.yaml",
            "configs/quality/scripts_lifecycle_registry.json",
            "configs/quality/technical_debt_audit_registry.yaml",
            "docs/02-architecture/current-state-inventory.md",
            "docs/04-reference/api/infrastructure.md",
            "reports/quality/total-tech-debt-audit-main-current.md",
            ".dockerignore",
            "mkdocs.yml",
            "docs/05-operations/runbooks/quality-tooling-artifact-refresh.md",
            "reports/quality/pytest-nodeid-inventory.json",
            "reports/quality/quality-move-qm08/reference_decisions.json",
            "scripts/engineering/README.md",
        ],
        repo_root=repo_root,
    )

    assert (
        "tests/architecture/test_github_actions_runtime_policy.py" in report["selected"]
    )
    assert "tests/unit/scripts/qa/test_topology_source_binding.py" in report["selected"]
    assert "tests/architecture/test_scripts_lifecycle_registry.py" in report["selected"]
    assert "tests/architecture/test_docker_runtime_contracts.py" in report["selected"]
    assert "tests/architecture/test_documentation_sync.py" in report["selected"]
    assert (
        "tests/unit/scripts/qa/test_refresh_governance_artifacts.py"
        in report["selected"]
    )
    assert (
        "tests/unit/scripts/qa/test_build_pytest_nodeid_inventory.py"
        in report["selected"]
    )
    assert (
        "tests/unit/scripts/engineering/qa/test_verify_quality_move.py"
        in report["selected"]
    )
    assert (
        "tests/architecture/test_scripts_inventory_discovery.py" in report["selected"]
    )
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
