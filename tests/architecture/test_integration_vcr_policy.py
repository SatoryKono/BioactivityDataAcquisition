"""Architecture tests for the tracked integration and VCR execution policy."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = ROOT / "configs" / "quality" / "integration_vcr_policy.yaml"
MATRIX_PATH = ROOT / "configs" / "quality" / "test_matrix.yaml"
CONFTST_PATH = ROOT / "tests" / "conftest.py"
TESTING_GUIDE_PATH = ROOT / "docs" / "03-guides" / "testing.md"


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
        assert (
            policy["supported_scopes"]["e2e"]["required_marker"] == "e2e"
        )
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

        assert vcr_policy["default_record_modes"] == {"ci": "none", "local": "once"}
        assert vcr_policy["supported_refresh_record_modes"] == ["new_episodes"]
        assert vcr_policy["legacy_compatibility_record_modes"] == ["all"]
        assert (
            'os.environ["VCR_RECORD_MODE"] = "none" if os.getenv("CI") else "once"'
            in conftest
        )
        assert "control-plane-e2e:" in tests_workflow
        assert policy["supported_scopes"]["e2e"]["ci_smoke_target"] in tests_workflow
        assert "VCR_RECORD_MODE=none uv run pytest" in tests_workflow
        assert "--vcr-record=none" in tests_workflow
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
            vcr_policy["canonical_root"]
            == fixture_governance["canonical_vcr_location"]
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
            "`partial` rollout",
            "reports/quality/vcr-metadata-catalog.json",
            "scripts/qa/report_vcr_metadata_catalog.py",
            "scripts/migrations/active/backfill_vcr_metadata_sidecars.py",
            ".github/vcr-noext-allowlist.txt",
            live_contract["repository_guard"],
            "BIOETL_LIVE_API_TESTS=true",
            "BIOETL_NETWORK_TESTS=true",
            live_contract["required_pytest_flag"],
        )

        for expected_anchor in required_guide_anchors:
            assert expected_anchor in testing_guide, (
                "testing guide drifted from the tracked integration/VCR policy: "
                f"missing {expected_anchor!r}"
            )

        assert "SatoryKono/BioactivityDataAcquisition2" not in testing_guide
