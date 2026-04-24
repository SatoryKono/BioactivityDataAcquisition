"""Architecture tests for the tracked integration and VCR execution policy."""

from __future__ import annotations

from pathlib import Path
import re

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "configs" / "quality" / "integration_vcr_policy.yaml"
MATRIX_PATH = ROOT / "configs" / "quality" / "test_matrix.yaml"
CONFTST_PATH = ROOT / "tests" / "conftest.py"
TESTING_GUIDE_PATH = ROOT / "docs" / "03-guides" / "testing.md"
DEV_README_PATH = ROOT / "scripts" / "engineering" / "dev" / "README.md"
QA_README_PATH = ROOT / "scripts" / "engineering" / "qa" / "README.md"
MIGRATIONS_README_PATH = ROOT / "scripts" / "ops" / "migrations" / "README.md"
CONTRIBUTING_PATH = ROOT / ".github" / "CONTRIBUTING.md"
VCR_TASKS_PATH = ROOT / "docs" / "05-operations" / "verification" / "vcr-test-tasks.md"
CURATED_INTEGRATION_MARKER_FILES = (
    Path("tests/integration/composite/test_column_naming_integration.py"),
    Path("tests/integration/composite/test_composite_config_backward_compatibility.py"),
    Path("tests/integration/infrastructure/storage/test_silver_writer.py"),
    Path("tests/integration/interfaces/test_cli_checkpoint_list.py"),
    Path("tests/integration/interfaces/test_cli_config_dq.py"),
    Path("tests/integration/interfaces/test_cli_maintenance_archive.py"),
    Path("tests/integration/interfaces/test_cli_maintenance_vacuum.py"),
    Path("tests/integration/interfaces/test_cli_quarantine_inspect.py"),
    Path("tests/integration/interfaces/test_cli_run_dry_run.py"),
    Path("tests/integration/interfaces/test_cli_run_incremental.py"),
    Path("tests/integration/interfaces/test_cli_shutdown_integration.py"),
    Path("tests/integration/test_grafana_config.py"),
    Path("tests/integration/test_prometheus_rules_config.py"),
)
CURATED_E2E_MARKER_FILES = (
    Path("tests/e2e/test_cli_safety.py"),
    Path("tests/e2e/test_e2e_stability_policy.py"),
)


def _iter_inventory_paths(node: object) -> list[str]:
    if isinstance(node, str):
        return [node]
    if isinstance(node, list):
        paths: list[str] = []
        for item in node:
            paths.extend(_iter_inventory_paths(item))
        return paths
    if isinstance(node, dict):
        paths: list[str] = []
        for item in node.values():
            paths.extend(_iter_inventory_paths(item))
        return paths
    return []


def _load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@pytest.mark.architecture
class TestIntegrationVcrPolicy:
    """Keep integration and VCR policy explicit and synchronized with repo reality."""

    def test_policy_file_is_present_and_scoped(self) -> None:
        policy = _load_yaml(POLICY_PATH)

        assert policy.get("policy_scope") == "integration_and_vcr_execution_policy"
        assert policy.get("issue_reference") == 2598

    def test_policy_points_to_tracked_source_of_truth_artifacts(self) -> None:
        policy = _load_yaml(POLICY_PATH)

        for relative_path in policy.get("source_of_truth", {}).values():
            assert (ROOT / relative_path).exists(), (
                f"integration/VCR policy source artifact missing: {relative_path}"
            )

    def test_supported_test_roots_and_execution_paths_exist(self) -> None:
        policy = _load_yaml(POLICY_PATH)

        integration_roots = policy["supported_scopes"]["integration"][
            "canonical_test_roots"
        ]
        for relative_path in integration_roots:
            assert (ROOT / relative_path).exists(), (
                f"integration/VCR policy references missing integration root: {relative_path}"
            )

        e2e_root = ROOT / policy["supported_scopes"]["e2e"]["canonical_test_root"]
        assert e2e_root.exists()
        assert policy["supported_scopes"]["e2e"]["required_marker"] == "e2e"
        ci_smoke_target = policy["supported_scopes"]["e2e"]["ci_smoke_target"]
        ci_smoke_file = ci_smoke_target.split("::", 1)[0]
        assert (ROOT / ci_smoke_file).exists()

        windows = policy["execution_paths"]["local"]["windows"]
        wsl = policy["execution_paths"]["local"]["wsl"]
        ci_uv = policy["execution_paths"]["local"]["ci_uv"]
        live_contract = policy["execution_paths"]["live_contract"]

        for relative_path in (
            windows["bootstrap"],
            windows["pytest_runner"],
            wsl["bootstrap"],
            wsl["pytest_runner"],
            ci_uv["workflow_path"],
            live_contract["workflow_path"],
        ):
            assert (ROOT / relative_path).exists(), (
                f"integration/VCR execution path missing: {relative_path}"
            )

        assert policy["supported_scopes"]["integration"]["supported_pipeline_families"]
        assert policy["supported_scopes"]["e2e"]["representative_pipeline_families"]

    def test_policy_declares_canonical_replay_and_refresh_examples(self) -> None:
        policy = _load_yaml(POLICY_PATH)
        windows = policy["execution_paths"]["local"]["windows"]
        wsl = policy["execution_paths"]["local"]["wsl"]
        ci_uv = policy["execution_paths"]["local"]["ci_uv"]
        live_contract = policy["execution_paths"]["live_contract"]
        refresh_protocol = policy["vcr_policy"]["refresh_protocol"]

        for command in (
            windows["replay_examples"]["integration"],
            windows["replay_examples"]["e2e"],
            windows["refresh_examples"]["targeted_integration"],
            windows["refresh_examples"]["targeted_e2e"],
            wsl["replay_examples"]["integration"],
            wsl["replay_examples"]["e2e"],
            wsl["refresh_examples"]["targeted_integration"],
            wsl["refresh_examples"]["targeted_e2e"],
            ci_uv["standard_replay_examples"]["control_plane_e2e"],
            live_contract["manual_command_example"],
        ):
            assert (
                "--vcr-record=none" in command
                or "--vcr-record=new_episodes" in command
                or "--network" in command
            )

        assert refresh_protocol["targeted_recording_only"] is True
        assert refresh_protocol["preferred_refresh_mode"] == "new_episodes"
        assert (
            "python -m scripts.engineering.qa.vcr check-secrets"
            in refresh_protocol["post_refresh_checks"]
        )
        assert (
            "python -m scripts.engineering.qa.vcr check-metadata-age --max-age-days 90"
            in refresh_protocol["post_refresh_checks"]
        )
        assert (
            "python -m scripts.engineering.qa report-vcr-metadata --check"
            in refresh_protocol["post_refresh_checks"]
        )

    def test_tracked_suite_inventory_matches_supported_matrix_and_markers(self) -> None:
        policy = _load_yaml(POLICY_PATH)
        inventory = policy["tracked_suite_inventory"]

        integration_smoke = policy["supported_scopes"]["integration"][
            "supported_pipeline_families"
        ]["pipeline_replay_smoke"]
        assert set(inventory["integration"]["pipeline_replay_smoke"]) == set(
            integration_smoke
        )

        e2e_provider_runs = policy["supported_scopes"]["e2e"][
            "representative_pipeline_families"
        ]["provider_runs"]
        assert set(inventory["e2e"]["provider_runs"]) == set(e2e_provider_runs)

        e2e_scenario_runs = policy["supported_scopes"]["e2e"][
            "representative_pipeline_families"
        ]["scenario_runs"]
        assert set(inventory["e2e"]["scenario_runs"]) == set(e2e_scenario_runs)

        for relative_path in inventory["integration"]["pipeline_replay_smoke"].values():
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            assert "pytest.mark.integration" in content, (
                "tracked integration pipeline replay surface must keep explicit integration marker: "
                f"{relative_path}"
            )

        for family_paths in inventory["integration"][
            "governance_and_runtime_surfaces"
        ].values():
            for relative_path in family_paths:
                content = (ROOT / relative_path).read_text(encoding="utf-8")
                assert "pytest.mark.integration" in content, (
                    "tracked governance/runtime integration surface must keep explicit integration marker: "
                    f"{relative_path}"
                )

        for relative_path in inventory["e2e"]["provider_runs"].values():
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            assert "pytest.mark.e2e" in content, (
                "tracked provider e2e surface must keep explicit e2e marker: "
                f"{relative_path}"
            )

        for relative_path in inventory["e2e"]["scenario_runs"].values():
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            assert "pytest.mark.e2e" in content, (
                "tracked scenario e2e surface must keep explicit e2e marker: "
                f"{relative_path}"
            )

    def test_every_test_surface_under_integration_and_e2e_is_in_tracked_inventory(
        self,
    ) -> None:
        policy = _load_yaml(POLICY_PATH)
        tracked_paths = {
            path.replace("\\", "/")
            for path in _iter_inventory_paths(policy["tracked_suite_inventory"])
        }
        repo_test_paths = {
            str(path.relative_to(ROOT)).replace("\\", "/")
            for root in (ROOT / "tests" / "integration", ROOT / "tests" / "e2e")
            for path in root.rglob("test_*.py")
        }

        assert tracked_paths == repo_test_paths, (
            "integration_vcr_policy tracked_suite_inventory must cover every "
            "integration/e2e test surface exactly. "
            f"missing={sorted(repo_test_paths - tracked_paths)} "
            f"extra={sorted(tracked_paths - repo_test_paths)}"
        )

    def test_policy_defaults_align_with_current_conftest_and_workflows(self) -> None:
        policy = _load_yaml(POLICY_PATH)
        tests_workflow = (
            ROOT / policy["execution_paths"]["local"]["ci_uv"]["workflow_path"]
        ).read_text(encoding="utf-8")
        contract_workflow = (
            ROOT / policy["execution_paths"]["live_contract"]["workflow_path"]
        ).read_text(encoding="utf-8")
        conftest = CONFTST_PATH.read_text(encoding="utf-8")
        vcr_policy = policy["vcr_policy"]

        assert vcr_policy["default_record_modes"] == {"ci": "none", "local": "none"}
        assert vcr_policy["supported_refresh_record_modes"] == ["new_episodes"]
        assert vcr_policy["legacy_compatibility_record_modes"] == ["all"]
        assert 'os.environ["VCR_RECORD_MODE"] = "none"' in conftest
        assert "control-plane-e2e:" in tests_workflow
        assert policy["supported_scopes"]["e2e"]["ci_smoke_target"] in tests_workflow
        assert "VCR_RECORD_MODE=none uv run pytest" in tests_workflow
        assert "--vcr-record=none" in tests_workflow
        assert (
            "python scripts/engineering/qa/vcr/check_root_vcr_cassettes.py"
            in tests_workflow
        )
        assert (
            "python scripts/engineering/qa/vcr/check_vcr_filename_policy.py"
            in tests_workflow
        )
        assert "tests/contract/ -v --tb=short --network" in contract_workflow
        assert (
            "github.repository == "
            f"'{policy['execution_paths']['live_contract']['repository_guard']}'"
            in contract_workflow
        )
        assert (
            policy["execution_paths"]["live_contract"]["required_pytest_flag"]
            in contract_workflow
        )
        for env_name, env_value in policy["execution_paths"]["live_contract"][
            "required_env"
        ].items():
            assert f'{env_name}: "{env_value}"' in contract_workflow
        assert (
            policy["execution_paths"]["live_contract"]["failure_issue_runbook_path"]
            in contract_workflow
        )
        assert "docs/RULES.md" not in contract_workflow

    def test_policy_matches_fixture_governance_and_contract_matrix(self) -> None:
        policy = _load_yaml(POLICY_PATH)
        matrix = _load_yaml(MATRIX_PATH)
        fixture_governance = matrix["fixture_governance"]
        contract_testing = matrix["contract_testing"]
        vcr_policy = policy["vcr_policy"]

        assert (
            vcr_policy["canonical_root"] == fixture_governance["canonical_vcr_location"]
        )
        assert (
            vcr_policy["extensionless_allowlist"]
            == fixture_governance["extensionless_allowlist"]
        )
        assert (
            vcr_policy["stale_age_days"]
            == fixture_governance["vcr_cassette_max_age_days"]
        )
        assert (
            vcr_policy["stale_age_requires_metadata"]
            == fixture_governance["cassette_staleness_requires_metadata"]
        )
        assert (
            vcr_policy["fixture_governance_rollout_source"]
            == fixture_governance["governance_ledger_location"]
        )
        assert (
            policy["execution_paths"]["live_contract"]["gate_mode"]
            == contract_testing["live_api_gate_mode"]
        )
        assert contract_testing["network_opt_in_required"] is True

    def test_incremental_extension_rules_require_tracked_policy_updates(self) -> None:
        policy = _load_yaml(POLICY_PATH)
        extension_rules = policy["incremental_extension_model"][
            "add_new_provider_or_pipeline_family"
        ]

        assert extension_rules, "incremental extension model must be explicit"
        assert any(
            "configs/quality/test_matrix.yaml" in rule for rule in extension_rules
        )
        assert any(
            "configs/quality/fixture_governance_ledger.yaml" in rule
            for rule in extension_rules
        )
        assert any("tests/fixtures/vcr/{provider}/" in rule for rule in extension_rules)

    def test_testing_guide_matches_current_fixture_governance_and_live_contract_policy(
        self,
    ) -> None:
        policy = _load_yaml(POLICY_PATH)
        testing_guide = TESTING_GUIDE_PATH.read_text(encoding="utf-8")
        live_contract = policy["execution_paths"]["live_contract"]

        required_guide_anchors = (
            "`enforced` rollout",
            "reports/quality/vcr-metadata-catalog.json",
            "scripts/engineering/qa/report_vcr_metadata_catalog.py",
            "scripts/ops/migrations/active/backfill_vcr_metadata_sidecars.py",
            ".github/vcr-noext-allowlist.txt",
            live_contract["repository_guard"],
            "BIOETL_LIVE_API_TESTS=true",
            "BIOETL_NETWORK_TESTS=true",
            live_contract["required_pytest_flag"],
            "--vcr-record=none",
            "--vcr-record=new_episodes",
            "chembl_activity",
            "pubchem_compound",
            "uniprot_protein",
        )

        for expected_anchor in required_guide_anchors:
            assert expected_anchor in testing_guide, (
                "testing guide drifted from the tracked integration/VCR policy: "
                f"missing {expected_anchor!r}"
            )

        assert not re.search(
            r"SatoryKono/BioactivityDataAcquisition2",
            testing_guide,
        )

    def test_dev_and_data_readmes_publish_policy_backed_execution_paths(self) -> None:
        policy = _load_yaml(POLICY_PATH)
        dev_readme = DEV_README_PATH.read_text(encoding="utf-8")
        qa_readme = QA_README_PATH.read_text(encoding="utf-8")
        migrations_readme = MIGRATIONS_README_PATH.read_text(encoding="utf-8")
        contributing = CONTRIBUTING_PATH.read_text(encoding="utf-8")

        assert "configs/quality/integration_vcr_policy.yaml" in dev_readme
        assert "docs/03-guides/testing.md" in dev_readme
        assert (
            policy["execution_paths"]["local"]["windows"]["replay_examples"][
                "integration"
            ]
            in dev_readme
        )
        assert (
            policy["execution_paths"]["local"]["wsl"]["replay_examples"]["integration"]
            in dev_readme
        )
        assert "--vcr-record=new_episodes" in dev_readme

        assert "report-vcr-metadata" in qa_readme
        assert "python scripts/engineering/qa/report_vcr_metadata_catalog.py --check" in qa_readme
        assert "backfill_vcr_metadata_sidecars.py" in migrations_readme
        assert (
            "scripts/ops/migrations/active/backfill_vcr_metadata_sidecars.py"
            in migrations_readme
        )

        assert "docs/03-guides/testing.md" in contributing
        assert "configs/quality/integration_vcr_policy.yaml" in contributing

    def test_curated_integration_and_e2e_surfaces_have_explicit_markers(self) -> None:
        for relative_path in CURATED_INTEGRATION_MARKER_FILES:
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            assert "pytest.mark.integration" in content, (
                "canonical integration surface drifted away from explicit integration markers: "
                f"{relative_path}"
            )

        for relative_path in CURATED_E2E_MARKER_FILES:
            content = (ROOT / relative_path).read_text(encoding="utf-8")
            assert "pytest.mark.e2e" in content, (
                "canonical e2e surface drifted away from explicit e2e markers: "
                f"{relative_path}"
            )

    def test_historical_vcr_tasks_doc_points_back_to_active_policy(self) -> None:
        historical_report = VCR_TASKS_PATH.read_text(encoding="utf-8")

        assert "Historical verification artifact (non-normative)" in historical_report
        assert "configs/quality/integration_vcr_policy.yaml" in historical_report
        assert "docs/03-guides/testing.md" in historical_report
        assert "configs/quality/test_matrix.yaml" in historical_report
