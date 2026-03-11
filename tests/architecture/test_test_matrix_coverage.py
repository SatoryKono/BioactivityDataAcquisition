"""Architecture tests for test matrix coverage validation.

Validates that provider test coverage meets ADR-042 requirements:
- VCR cassettes exist for each provider
- Unit tests exist for each architectural layer
- Property tests stay within allowed boundaries
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = ROOT / "tests"
MATRIX_PATH = ROOT / "configs" / "quality" / "test_matrix.yaml"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"


def _load_matrix() -> dict:
    """Load the test matrix configuration."""
    with MATRIX_PATH.open() as f:
        return yaml.safe_load(f)


@pytest.mark.architecture
class TestVCRCassetteCoverage:
    """Validate VCR cassettes exist for required providers."""

    def test_vcr_dir_exists_for_each_provider(self) -> None:
        matrix = _load_matrix()
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"
        for provider, config in matrix["providers"].items():
            if config.get("vcr_cassettes") == "MUST":
                provider_vcr = vcr_dir / provider
                assert provider_vcr.is_dir(), (
                    f"Missing VCR cassette directory for provider '{provider}': "
                    f"{provider_vcr}"
                )

    def test_vcr_cassettes_not_empty(self) -> None:
        matrix = _load_matrix()
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"
        for provider, config in matrix["providers"].items():
            if config.get("vcr_cassettes") == "MUST":
                provider_vcr = vcr_dir / provider
                if provider_vcr.is_dir():
                    cassettes = list(provider_vcr.glob("*.yaml"))
                    assert len(cassettes) > 0, (
                        f"Provider '{provider}' VCR directory exists but has no cassettes"
                    )


@pytest.mark.architecture
class TestPropertyTestBoundaries:
    """Validate property-based tests respect ADR-042 boundaries."""

    def test_no_hypothesis_in_forbidden_dirs(self) -> None:
        """Property tests MUST NOT exist in forbidden directories."""
        matrix = _load_matrix()
        forbidden = matrix.get("property_test_boundaries", {}).get("forbidden", [])

        for forbidden_path in forbidden:
            # Map source path to test path
            parts = forbidden_path.split("/")
            if len(parts) >= 2:
                test_dir = TESTS_DIR / "unit" / parts[0] / parts[1]
            else:
                test_dir = TESTS_DIR / "unit" / parts[0]

            if not test_dir.is_dir():
                continue

            for test_file in test_dir.rglob("test_*.py"):
                content = test_file.read_text(encoding="utf-8")
                if "@given(" in content or "from hypothesis" in content:
                    # Allow if explicitly marked as exception
                    if "# hypothesis: boundary-exception" in content:
                        continue
                    pytest.fail(
                        f"Property-based test found in forbidden directory: "
                        f"{test_file.relative_to(ROOT)}"
                    )


@pytest.mark.architecture
class TestLayerTestCoverage:
    """Validate each layer has required test types."""

    def test_unit_tests_exist_per_layer(self) -> None:
        """Each layer with unit: MUST should have unit tests."""
        matrix = _load_matrix()
        for layer, config in matrix["layers"].items():
            if config.get("unit") == "MUST":
                layer_test_dir = TESTS_DIR / "unit" / layer
                if not layer_test_dir.is_dir():
                    # Try alternative naming
                    layer_test_dir = TESTS_DIR / "unit" / layer
                if layer_test_dir.is_dir():
                    test_files = list(layer_test_dir.rglob("test_*.py"))
                    assert len(test_files) > 0, (
                        f"Layer '{layer}' requires unit tests but none found in "
                        f"{layer_test_dir.relative_to(ROOT)}"
                    )


@pytest.mark.architecture
class TestFixtureGovernanceRollout:
    """Validate staged fixture-governance declarations match repository state."""

    def test_fixture_governance_rollout_matches_current_inventory(self) -> None:
        matrix = _load_matrix()
        fixture_governance = matrix.get("fixture_governance", {})
        rollout = fixture_governance.get("rollout", {})
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"
        golden_dir = TESTS_DIR / "fixtures" / "golden"
        contract_dir = TESTS_DIR / "fixtures" / "contracts"
        current_snapshot_dir = ROOT / fixture_governance["current_silver_schema_snapshot_location"]

        metadata_files = list(vcr_dir.rglob("*_meta.yaml")) if vcr_dir.exists() else []
        golden_files = list(golden_dir.rglob("*")) if golden_dir.exists() else []
        contract_files = list(contract_dir.rglob("*")) if contract_dir.exists() else []
        current_snapshot_files = (
            list(current_snapshot_dir.rglob("*.json")) if current_snapshot_dir.exists() else []
        )

        assert rollout.get("cassette_metadata") in {"planned", "partial", "enforced"}
        assert rollout.get("cassette_staleness_age") in {"planned", "partial", "enforced"}
        assert rollout.get("golden_masters") in {"planned", "partial", "enforced"}
        assert rollout.get("contract_snapshots") in {"planned", "partial", "enforced"}

        if fixture_governance.get("cassette_metadata_required"):
            assert rollout.get("cassette_metadata") == "enforced"
            assert metadata_files, "cassette metadata is required but *_meta.yaml files are missing"
        else:
            assert rollout.get("cassette_metadata") in {"planned", "partial"}

        if contract_files:
            assert rollout.get("contract_snapshots") in {"partial", "enforced"}
        else:
            assert rollout.get("contract_snapshots") == "planned"
            assert current_snapshot_files, (
                "external contract snapshot registry is still planned, but current "
                "silver schema snapshots are also missing"
            )

        if golden_files:
            assert rollout.get("golden_masters") in {"partial", "enforced"}
        else:
            assert rollout.get("golden_masters") == "planned"

    def test_vcr_filename_and_placement_policy_match_current_ci_contract(self) -> None:
        matrix = _load_matrix()
        fixture_governance = matrix.get("fixture_governance", {})
        rollout = fixture_governance.get("rollout", {})
        workflow = (WORKFLOWS_DIR / "tests.yml").read_text(encoding="utf-8")
        allowlist_path = ROOT / fixture_governance["extensionless_allowlist"]
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"
        legacy_dir = TESTS_DIR / "fixtures" / "vcr_cassettes"

        extensionless = [
            path.relative_to(ROOT).as_posix()
            for path in vcr_dir.rglob("*")
            if path.is_file() and path.name != ".gitkeep" and "." not in path.name
        ]
        from_root_markers = list(vcr_dir.rglob("*.from_root.yaml"))

        assert fixture_governance.get("root_vcr_policy_enforced") is True
        assert rollout.get("extensionless_filenames") in {"partial", "enforced"}
        assert "python scripts/check_root_vcr_cassettes.py" in workflow
        assert "python scripts/check_vcr_filename_policy.py" in workflow
        assert not legacy_dir.exists(), "legacy tests/fixtures/vcr_cassettes directory must stay removed"
        assert not from_root_markers, "legacy *.from_root.yaml markers must stay removed"

        if rollout.get("extensionless_filenames") == "partial":
            assert allowlist_path.exists(), "partial extensionless rollout requires an allowlist file"
            allowlist_entries = {
                line.strip()
                for line in allowlist_path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            }
            assert extensionless, "partial extensionless rollout is declared but no extensionless files remain"
            assert set(extensionless) <= allowlist_entries, (
                "extensionless VCR inventory must stay fully allowlisted during partial rollout"
            )
        else:
            assert not extensionless, "enforced extensionless rollout must not leave extensionless VCR files"

    def test_vcr_cassette_age_rollout_matches_metadata_backfill_state(self) -> None:
        matrix = _load_matrix()
        fixture_governance = matrix.get("fixture_governance", {})
        rollout = fixture_governance.get("rollout", {})
        workflow = (WORKFLOWS_DIR / "tests.yml").read_text(encoding="utf-8")
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"
        metadata_files = list(vcr_dir.rglob("*_meta.yaml")) if vcr_dir.exists() else []

        assert fixture_governance.get("vcr_cassette_max_age_days") == 90
        assert rollout.get("cassette_staleness_age") in {"planned", "partial", "enforced"}

        if rollout.get("cassette_staleness_age") == "planned":
            assert fixture_governance.get("cassette_metadata_required") is False
            assert not metadata_files, (
                "planned cassette stale-age rollout must be updated once *_meta.yaml backfill begins"
            )
            assert "check_vcr_cassette_age" not in workflow
            assert "check_vcr_metadata_age" not in workflow
        elif rollout.get("cassette_staleness_age") == "partial":
            assert metadata_files, "partial cassette stale-age rollout requires *_meta.yaml inventory"
        else:
            assert fixture_governance.get("cassette_metadata_required") is True
            assert metadata_files, "enforced cassette stale-age rollout requires *_meta.yaml inventory"

    def test_vcr_metadata_catalog_and_backfill_policy_match_current_state(self) -> None:
        matrix = _load_matrix()
        fixture_governance = matrix.get("fixture_governance", {})
        rollout = fixture_governance.get("rollout", {})
        workflow = (WORKFLOWS_DIR / "tests.yml").read_text(encoding="utf-8")
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"
        metadata_files = list(vcr_dir.rglob("*_meta.yaml")) if vcr_dir.exists() else []
        catalog_path = ROOT / fixture_governance["cassette_metadata_catalog_location"]
        catalog_script = ROOT / fixture_governance["cassette_metadata_catalog_script"]
        backfill_script = ROOT / fixture_governance["cassette_metadata_backfill_script"]

        assert rollout.get("cassette_metadata_catalog") in {"planned", "partial", "enforced"}
        assert rollout.get("cassette_metadata_backfill") in {"planned", "partial", "enforced"}
        assert fixture_governance.get("cassette_metadata_backfill_workflow_present") in {True, False}

        if rollout.get("cassette_metadata_catalog") == "planned":
            assert not catalog_path.exists(), (
                "planned metadata catalog rollout must be updated once the canonical catalog exists"
            )
        else:
            assert catalog_path.exists(), "active metadata catalog rollout requires canonical catalog artifact"

        if rollout.get("cassette_metadata_backfill") == "planned":
            assert fixture_governance.get("cassette_metadata_backfill_workflow_present") is False
            assert not metadata_files, (
                "planned metadata backfill rollout must be updated once *_meta.yaml inventory appears"
            )
            assert not catalog_script.exists(), (
                "planned metadata catalog rollout must be updated once the canonical generator exists"
            )
            assert not backfill_script.exists(), (
                "planned metadata backfill rollout must be updated once the canonical migration exists"
            )
            assert "backfill_vcr_metadata" not in workflow
            assert "generate_vcr_metadata_catalog" not in workflow
        else:
            assert metadata_files, "active metadata backfill rollout requires *_meta.yaml inventory"


@pytest.mark.architecture
class TestMutationTestingRollout:
    """Validate mutation-testing matrix stays aligned with workflow reality."""

    def test_mutation_matrix_matches_current_workflow_contract(self) -> None:
        matrix = _load_matrix()
        mutation = matrix.get("mutation_testing", {})
        workflow = (WORKFLOWS_DIR / "mutation-testing.yml").read_text(encoding="utf-8")

        assert mutation.get("enabled") is True
        assert mutation.get("workflow_present") is True
        assert mutation.get("ci_gate_mode") in {"partial", "full"}
        assert mutation["targets"]["domain"]["min_score"] == 70
        assert mutation["targets"]["domain"]["enforced"] is True
        assert mutation["targets"]["application"]["min_score"] == 60
        assert mutation["targets"]["application"]["enforced"] is False

        assert "mutmut run --paths-to-mutate=src/bioetl/domain/" in workflow
        assert "THRESHOLD = 70.0" in workflow
        assert "--paths-to-mutate=src/bioetl/application/" not in workflow
        assert mutation.get("ci_gate_mode") == "partial"


@pytest.mark.architecture
class TestContractTestingGovernance:
    """Validate contract-testing workflow stays aligned with matrix declarations."""

    def test_contract_testing_matrix_matches_current_workflow_contract(self) -> None:
        matrix = _load_matrix()
        contract_testing = matrix.get("contract_testing", {})
        workflow = (WORKFLOWS_DIR / "contract-tests.yml").read_text(encoding="utf-8")

        assert contract_testing.get("workflow_present") is True
        assert contract_testing.get("live_api_gate_mode") == "scheduled"
        assert contract_testing.get("network_opt_in_required") is True
        assert contract_testing["provider_live_api"]["chembl"] == "enforced"
        assert contract_testing["provider_live_api"]["pubchem"] == "enforced"
        assert contract_testing["provider_live_api"]["uniprot"] == "enforced"
        assert contract_testing["provider_live_api"]["pubmed"] == "enforced"
        assert contract_testing["provider_live_api"]["crossref"] == "planned"
        assert contract_testing["provider_live_api"]["openalex"] == "planned"
        assert contract_testing["provider_live_api"]["semanticscholar"] == "planned"

        assert "BIOETL_LIVE_API_TESTS: \"true\"" in workflow
        assert "BIOETL_NETWORK_TESTS: \"true\"" in workflow
        assert "tests/contract/ -v --tb=short --network" in workflow
        assert "cron: '0 2 1 * *'" in workflow
        assert "Create Issue on Failure" in workflow

    def test_enforced_live_contract_providers_have_test_modules_and_markers(self) -> None:
        matrix = _load_matrix()
        provider_live_api = matrix["contract_testing"]["provider_live_api"]
        contract_dir = TESTS_DIR / "contract"
        conftest = (contract_dir / "conftest.py").read_text(encoding="utf-8")

        for provider, status in provider_live_api.items():
            contract_test = contract_dir / f"test_{provider}_contract.py"
            marker_registration = f'"markers", "{provider}:'

            if status == "enforced":
                assert contract_test.exists(), (
                    f"provider '{provider}' is live-enforced but {contract_test.relative_to(ROOT)} is missing"
                )
                assert marker_registration in conftest, (
                    f"provider '{provider}' is live-enforced but pytest marker is not registered"
                )
            elif status == "planned":
                assert not contract_test.exists(), (
                    f"provider '{provider}' is still planned but already has a live contract suite; "
                    "promote matrix status before enabling enforcement"
                )
