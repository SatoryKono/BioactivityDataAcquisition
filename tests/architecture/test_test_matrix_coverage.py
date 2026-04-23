"""Architecture tests for test matrix coverage validation.

Validates that provider test coverage meets ADR-042 requirements:
- VCR cassettes exist for each provider
- Unit tests exist for each architectural layer
- Property tests stay within allowed boundaries
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
TESTS_DIR = ROOT / "tests"
MATRIX_PATH = ROOT / "configs" / "quality" / "test_matrix.yaml"
WORKFLOWS_DIR = ROOT / ".github" / "workflows"
ENTITY_CONFIGS_DIR = ROOT / "configs" / "entities"
YamlMap = dict[str, Any]


def _load_matrix() -> YamlMap:
    """Load the test matrix configuration."""
    with MATRIX_PATH.open() as f:
        return cast(YamlMap, yaml.safe_load(f))


def _iter_entity_configs() -> list[tuple[str, str, Path]]:
    """Return active entity config tuples as (provider, entity, path)."""
    configs: list[tuple[str, str, Path]] = []
    for config_path in sorted(ENTITY_CONFIGS_DIR.glob("*/*.yaml")):
        configs.append((config_path.parent.name, config_path.stem, config_path))
    return configs


def _ownership_paths(matrix: YamlMap, entity_key: str) -> list[Path]:
    """Resolve owned test paths for a provider.entity key."""
    raw_paths = matrix.get("entity_test_ownership", {}).get(entity_key, [])
    if isinstance(raw_paths, str):
        raw_paths = [raw_paths]
    return [ROOT / path for path in raw_paths]


def _forbidden_test_dir(forbidden_path: str) -> Path:
    parts = forbidden_path.split("/")
    if len(parts) >= 2:
        return TESTS_DIR / "unit" / parts[0] / parts[1]
    return TESTS_DIR / "unit" / parts[0]


def _contains_forbidden_hypothesis_usage(content: str) -> bool:
    if "@given(" not in content and "from hypothesis" not in content:
        return False
    return "# hypothesis: boundary-exception" not in content


def _required_provider_names(matrix: YamlMap, field: str) -> list[str]:
    return [
        provider
        for provider, config in matrix["providers"].items()
        if config.get(field) == "MUST"
    ]


def _must_unit_layers(matrix: YamlMap) -> list[str]:
    return [
        layer
        for layer, config in matrix["layers"].items()
        if config.get("unit") == "MUST"
    ]


def _provider_suite_index(provider_suites: Any) -> dict[str, set[str]]:
    suite_index: dict[str, set[str]] = {}
    for suite_name, suite_config in provider_suites.items():
        for provider in suite_config.get("providers", {}):
            suite_index.setdefault(provider, set()).add(suite_name)
    return suite_index


def _lane_paths(lane: YamlMap) -> list[Path]:
    return [ROOT / str(path) for path in lane.get("paths", [])]


def _lane_runner(lane: YamlMap) -> Path:
    return ROOT / str(lane.get("runner"))


def _represented_golden_master_entities() -> dict[str, set[str]]:
    from tests.architecture.test_config_golden_master import PIPELINES

    represented: dict[str, set[str]] = {}
    for provider, entity, config_path in _iter_entity_configs():
        lines = config_path.read_text(encoding="utf-8").splitlines()
        pipeline_name = next(
            line.split(":", 1)[1].strip() for line in lines if "pipeline_name:" in line
        )
        if pipeline_name in PIPELINES:
            represented.setdefault(provider, set()).add(entity)
    return represented


@pytest.mark.architecture
class TestVCRCassetteCoverage:
    """Validate VCR cassettes exist for required providers."""

    def test_vcr_dir_exists_for_each_provider(self) -> None:
        matrix = _load_matrix()
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"
        for provider in _required_provider_names(matrix, "vcr_cassettes"):
            provider_vcr = vcr_dir / provider
            assert provider_vcr.is_dir(), (
                f"Missing VCR cassette directory for provider '{provider}': "
                f"{provider_vcr}"
            )

    def test_vcr_cassettes_not_empty(self) -> None:
        matrix = _load_matrix()
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"
        for provider in _required_provider_names(matrix, "vcr_cassettes"):
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
            test_dir = _forbidden_test_dir(forbidden_path)

            if not test_dir.is_dir():
                continue

            for test_file in test_dir.rglob("test_*.py"):
                content = test_file.read_text(encoding="utf-8")
                if _contains_forbidden_hypothesis_usage(content):
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
        for layer in _must_unit_layers(matrix):
            layer_test_dir = TESTS_DIR / "unit" / layer
            if layer_test_dir.is_dir():
                test_files = list(layer_test_dir.rglob("test_*.py"))
                assert len(test_files) > 0, (
                    f"Layer '{layer}' requires unit tests but none found in "
                    f"{layer_test_dir.relative_to(ROOT)}"
                )


@pytest.mark.architecture
class TestCanonicalTestLanes:
    """Validate named test-health lanes stay stable and wrapper-ready."""

    EXPECTED_LANES = {
        "smoke",
        "unit-fast",
        "integration-replay",
        "security",
        "contracts",
        "architecture",
        "e2e",
        "memory",
        "performance",
        "coverage-verify",
    }

    def test_matrix_declares_exact_canonical_test_lanes(self) -> None:
        matrix = _load_matrix()
        test_lanes = matrix.get("test_lanes", {})
        lanes = test_lanes.get("lanes", {})
        execution_defaults = test_lanes.get("execution_defaults", {})

        assert test_lanes.get("schema_version") == 1
        assert execution_defaults.get("pythonpath") == "src"
        assert (
            execution_defaults.get("direct_runner")
            == "scripts/engineering/dev/run_pytest.sh"
        )
        assert (
            execution_defaults.get("sharded_runner")
            == "scripts/engineering/dev/run_pytest_sharded.sh"
        )
        assert set(lanes) == self.EXPECTED_LANES

        for lane_name, lane in lanes.items():
            assert lane.get("suite_name") == lane_name
            assert lane.get("description")
            assert lane.get("marker_expression")
            assert lane.get("pytest_args")
            assert lane.get("runner_backend") in {
                "run_pytest",
                "run_pytest_sharded",
            }
            assert lane.get("runner")
            assert lane.get("coverage_gate") in {"none", "repo-wide"}
            assert lane.get("replay_mode") in {
                "mixed",
                "not_applicable",
                "replay_or_no_api",
                "vcr_replay_only",
            }
            artifacts = lane.get("expected_artifacts", {})
            assert artifacts.get("junit_xml") is True
            assert artifacts.get("json_summary") is True

    def test_canonical_test_lane_paths_and_runners_exist(self) -> None:
        matrix = _load_matrix()
        lanes = matrix["test_lanes"]["lanes"]

        for lane_name, lane in lanes.items():
            runner = _lane_runner(lane)
            assert runner.exists(), (
                f"{lane_name} references missing runner: {runner.relative_to(ROOT)}"
            )

            paths = _lane_paths(lane)
            assert paths, f"{lane_name} must declare at least one path"
            for path in paths:
                assert path.exists(), (
                    f"{lane_name} references missing test path: "
                    f"{path.relative_to(ROOT)}"
                )

    def test_only_coverage_verify_enforces_repo_wide_coverage(self) -> None:
        matrix = _load_matrix()
        lanes = matrix["test_lanes"]["lanes"]

        repo_wide_coverage_lanes = {
            lane_name
            for lane_name, lane in lanes.items()
            if lane.get("coverage_gate") == "repo-wide"
        }
        lanes_with_coverage_args = {
            lane_name
            for lane_name, lane in lanes.items()
            if any(str(arg).startswith("--cov") for arg in lane.get("pytest_args", []))
        }

        assert repo_wide_coverage_lanes == {"coverage-verify"}
        assert lanes_with_coverage_args == {"coverage-verify"}

    def test_lane_marker_boundaries_match_current_policy(self) -> None:
        matrix = _load_matrix()
        lanes = matrix["test_lanes"]["lanes"]

        assert (
            lanes["smoke"]["marker_expression"] == "not benchmark and not memory"
        )
        assert (
            lanes["unit-fast"]["marker_expression"]
            == "not slow and not benchmark and not memory"
        )
        assert lanes["integration-replay"]["replay_mode"] == "vcr_replay_only"
        assert "--vcr-record=none" in lanes["integration-replay"]["pytest_args"]
        assert (
            lanes["security"]["marker_expression"]
            == "security and not benchmark and not memory"
        )
        assert lanes["architecture"]["runner_backend"] == "run_pytest_sharded"
        assert "S7-crosscutting-architecture" in lanes["architecture"]["runner_options"]
        assert lanes["memory"]["marker_expression"] == "memory and not benchmark"
        assert lanes["performance"]["marker_expression"] == "benchmark and performance"
        assert "-p" in lanes["performance"]["pytest_args"]
        assert "no:xdist" in lanes["performance"]["pytest_args"]
        assert lanes["coverage-verify"]["runner_backend"] == "run_pytest_sharded"
        assert "--keep-coverage-files" in lanes["coverage-verify"]["runner_options"]
        assert (
            lanes["coverage-verify"]["marker_expression"]
            == "not e2e and not benchmark and not memory"
        )


@pytest.mark.architecture
class TestEntityOwnershipCoverage:
    """Validate provider/entity test ownership ratchets."""

    def test_each_active_provider_entity_has_test_ownership_entry(self) -> None:
        matrix = _load_matrix()
        ownership = matrix.get("entity_test_ownership", {})

        for provider, entity, _config_path in _iter_entity_configs():
            entity_key = f"{provider}.{entity}"
            assert entity_key in ownership, (
                f"Missing entity_test_ownership entry for '{entity_key}' in "
                f"{MATRIX_PATH.relative_to(ROOT)}"
            )

    def test_owned_test_paths_exist_for_declared_entities(self) -> None:
        matrix = _load_matrix()

        for provider, entity, _config_path in _iter_entity_configs():
            entity_key = f"{provider}.{entity}"
            owned_paths = _ownership_paths(matrix, entity_key)

            assert owned_paths, (
                f"entity '{entity_key}' must declare at least one test path"
            )
            for owned_path in owned_paths:
                assert owned_path.exists(), (
                    f"Declared ownership path for '{entity_key}' is missing: "
                    f"{owned_path.relative_to(ROOT)}"
                )

    def test_must_contract_providers_have_owned_contract_or_provider_regression_suite(
        self,
    ) -> None:
        matrix = _load_matrix()
        provider_suites = matrix.get("provider_regression_suites", {})
        contract_dir = TESTS_DIR / "contract"
        suite_index = _provider_suite_index(provider_suites)

        for provider in _required_provider_names(matrix, "contract_tests"):
            contract_path = contract_dir / f"test_{provider}_contract.py"
            assert contract_path.exists() or provider in suite_index, (
                f"provider '{provider}' requires contract coverage but has neither "
                f"{contract_path.relative_to(ROOT)} nor a canonical provider regression suite"
            )

    def test_golden_master_representative_set_matches_matrix_policy(self) -> None:
        matrix = _load_matrix()
        represented = _represented_golden_master_entities()

        for provider, config in matrix["providers"].items():
            if provider == "chembl":
                continue
            if config.get("golden_masters") in {"SHOULD", "MAY"}:
                assert provider in represented, (
                    f"provider '{provider}' is eligible for golden-master coverage but "
                    "is missing from the representative pipeline set"
                )

    def test_provider_matrix_only_references_existing_entity_configs(self) -> None:
        matrix = _load_matrix()
        existing = {
            (provider, entity) for provider, entity, _ in _iter_entity_configs()
        }

        for provider, config in matrix["providers"].items():
            for entity in config.get("entities", []):
                assert (provider, entity) in existing, (
                    f"matrix references missing entity config '{provider}.{entity}'"
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
        current_snapshot_dir = (
            ROOT / fixture_governance["current_silver_schema_snapshot_location"]
        )

        metadata_files = list(vcr_dir.rglob("*_meta.yaml")) if vcr_dir.exists() else []
        golden_files = list(golden_dir.rglob("*")) if golden_dir.exists() else []
        contract_files = list(contract_dir.rglob("*")) if contract_dir.exists() else []
        current_snapshot_files = (
            list(current_snapshot_dir.rglob("*.json"))
            if current_snapshot_dir.exists()
            else []
        )

        assert rollout.get("cassette_metadata") in {"planned", "partial", "enforced"}
        assert rollout.get("cassette_staleness_age") in {
            "metadata_gated",
            "partial",
            "enforced",
        }
        assert rollout.get("golden_masters") in {"planned", "partial", "enforced"}
        assert rollout.get("contract_snapshots") in {"planned", "partial", "enforced"}

        if fixture_governance.get("cassette_metadata_required"):
            assert rollout.get("cassette_metadata") == "enforced"
            assert metadata_files, (
                "cassette metadata is required but *_meta.yaml files are missing"
            )
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
        assert (
            "python scripts/engineering/qa/vcr/check_root_vcr_cassettes.py" in workflow
        )
        assert (
            "python scripts/engineering/qa/vcr/check_vcr_filename_policy.py" in workflow
        )
        assert not legacy_dir.exists(), (
            "legacy tests/fixtures/vcr_cassettes directory must stay removed"
        )
        assert not from_root_markers, (
            "legacy *.from_root.yaml markers must stay removed"
        )

        if rollout.get("extensionless_filenames") == "partial":
            assert allowlist_path.exists(), (
                "partial extensionless rollout requires an allowlist file"
            )
            allowlist_entries = {
                line.strip()
                for line in allowlist_path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.lstrip().startswith("#")
            }
            assert extensionless, (
                "partial extensionless rollout is declared but no extensionless files remain"
            )
            assert set(extensionless) <= allowlist_entries, (
                "extensionless VCR inventory must stay fully allowlisted during partial rollout"
            )
        else:
            assert not extensionless, (
                "enforced extensionless rollout must not leave extensionless VCR files"
            )

    def test_vcr_cassette_age_rollout_matches_metadata_backfill_state(self) -> None:
        matrix = _load_matrix()
        fixture_governance = matrix.get("fixture_governance", {})
        rollout = fixture_governance.get("rollout", {})
        workflow = (WORKFLOWS_DIR / "tests.yml").read_text(encoding="utf-8")
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"
        metadata_files = list(vcr_dir.rglob("*_meta.yaml")) if vcr_dir.exists() else []

        assert fixture_governance.get("vcr_cassette_max_age_days") == 90
        assert rollout.get("cassette_staleness_age") in {
            "metadata_gated",
            "partial",
            "enforced",
        }
        assert fixture_governance.get("cassette_staleness_requires_metadata") in {
            True,
            False,
        }

        if rollout.get("cassette_staleness_age") == "metadata_gated":
            assert (
                fixture_governance.get("cassette_staleness_requires_metadata") is True
            )
            assert fixture_governance.get("cassette_metadata_required") is False
            assert not metadata_files, (
                "metadata-gated cassette stale-age policy must be updated once *_meta.yaml backfill begins"
            )
            assert "check_vcr_cassette_age" not in workflow
            assert "check_vcr_metadata_age" not in workflow
        elif rollout.get("cassette_staleness_age") == "partial":
            assert (
                fixture_governance.get("cassette_staleness_requires_metadata") is True
            )
            assert metadata_files, (
                "partial cassette stale-age rollout requires *_meta.yaml inventory"
            )
        else:
            assert (
                fixture_governance.get("cassette_staleness_requires_metadata") is True
            )
            assert fixture_governance.get("cassette_metadata_required") is True
            assert metadata_files, (
                "enforced cassette stale-age rollout requires *_meta.yaml inventory"
            )

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

        assert rollout.get("cassette_metadata_catalog") in {
            "planned",
            "partial",
            "enforced",
        }
        assert rollout.get("cassette_metadata_backfill") in {
            "planned",
            "partial",
            "enforced",
        }
        assert fixture_governance.get(
            "cassette_metadata_backfill_workflow_present"
        ) in {True, False}

        if rollout.get("cassette_metadata_catalog") == "planned":
            assert not catalog_path.exists(), (
                "planned metadata catalog rollout must be updated once the canonical catalog exists"
            )
        else:
            assert catalog_path.exists(), (
                "active metadata catalog rollout requires canonical catalog artifact"
            )

        if rollout.get("cassette_metadata_backfill") == "planned":
            assert (
                fixture_governance.get("cassette_metadata_backfill_workflow_present")
                is False
            )
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
            assert metadata_files, (
                "active metadata backfill rollout requires *_meta.yaml inventory"
            )


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
class TestContractSnapshotGovernance:
    """Validate the bounded live-provider contract snapshot rollout slice."""

    def test_bounded_contract_snapshot_registry_matches_managed_slice(self) -> None:
        matrix = _load_matrix()
        fixture_governance = matrix.get("fixture_governance", {})
        registry = fixture_governance.get("contract_snapshot_registry", {})
        providers = registry.get("providers", {})

        assert (
            fixture_governance.get("rollout", {}).get("contract_snapshots") == "partial"
        )
        assert registry.get("scope") == "bounded_live_provider_baseline"
        assert registry.get("update_env_var") == "UPDATE_SNAPSHOTS"

        documentation_path = ROOT / registry["documentation"]
        helper_module_path = ROOT / registry["helper_module"]
        registry_test_path = ROOT / registry["registry_test_module"]
        assert documentation_path.exists()
        assert helper_module_path.exists()
        assert registry_test_path.exists()
        assert set(providers) == {
            "chembl",
            "crossref",
            "openalex",
            "pubchem",
            "pubmed",
            "semanticscholar",
            "uniprot",
        }

        for provider, provider_config in providers.items():
            version = provider_config["version"]
            snapshot_path = (
                TESTS_DIR / "fixtures" / "contracts" / provider / f"v{version}.json"
            )
            assert snapshot_path.exists(), (
                f"bounded snapshot registry is missing canonical snapshot for '{provider}'"
            )

            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
            assert snapshot["provider"] == provider
            assert snapshot["version"] == version
            assert set(provider_config["required_probes"]).issubset(snapshot["probes"])

            test_module_path = ROOT / provider_config["test_module"]
            assert test_module_path.exists(), (
                f"bounded snapshot registry is missing drift test module for '{provider}'"
            )


@pytest.mark.architecture
class TestContractTestingGovernance:
    """Validate contract-testing workflow stays aligned with matrix declarations."""

    def test_contract_testing_matrix_matches_current_workflow_contract(self) -> None:
        matrix = _load_matrix()
        contract_testing = matrix.get("contract_testing", {})
        workflow = (WORKFLOWS_DIR / "contract-tests.yml").read_text(encoding="utf-8")
        live_api_baseline = contract_testing.get("live_api_minimum_baseline", {})

        assert contract_testing.get("workflow_present") is True
        assert contract_testing.get("live_api_gate_mode") == "scheduled"
        assert contract_testing.get("network_opt_in_required") is True
        assert live_api_baseline == {
            "enforced_providers": [
                "chembl",
                "pubchem",
                "uniprot",
                "pubmed",
                "crossref",
                "openalex",
                "semanticscholar",
            ],
            "pilot_providers": [],
            "vcr_only_providers": [],
        }
        assert contract_testing["provider_live_api"]["chembl"] == "enforced"
        assert contract_testing["provider_live_api"]["pubchem"] == "enforced"
        assert contract_testing["provider_live_api"]["uniprot"] == "enforced"
        assert contract_testing["provider_live_api"]["pubmed"] == "enforced"
        assert contract_testing["provider_live_api"]["crossref"] == "enforced"
        assert contract_testing["provider_live_api"]["openalex"] == "enforced"
        assert contract_testing["provider_live_api"]["semanticscholar"] == "enforced"

        assert 'BIOETL_LIVE_API_TESTS: "true"' in workflow
        assert 'BIOETL_NETWORK_TESTS: "true"' in workflow
        assert "tests/contract/ -v --tb=short --network" in workflow
        assert "cron: '0 2 1 * *'" in workflow
        assert "Create Issue on Failure" in workflow

    def test_enforced_live_contract_providers_have_test_modules_and_markers(
        self,
    ) -> None:
        matrix = _load_matrix()
        contract_testing = matrix["contract_testing"]
        provider_live_api = contract_testing["provider_live_api"]
        live_api_baseline = contract_testing["live_api_minimum_baseline"]
        providers = matrix["providers"]
        contract_dir = TESTS_DIR / "contract"
        conftest = (contract_dir / "conftest.py").read_text(encoding="utf-8")
        vcr_dir = TESTS_DIR / "fixtures" / "vcr"

        for provider, status in provider_live_api.items():
            contract_test = contract_dir / f"test_{provider}_contract.py"
            marker_registration = f'"markers", "{provider}:'

            if status in {"enforced", "pilot"}:
                assert contract_test.exists(), (
                    f"provider '{provider}' is {status} but {contract_test.relative_to(ROOT)} is missing"
                )
                assert marker_registration in conftest, (
                    f"provider '{provider}' is {status} but pytest marker is not registered"
                )
                if status == "pilot":
                    assert provider in live_api_baseline.get("pilot_providers", []), (
                        f"provider '{provider}' is marked pilot but not tracked in pilot_providers baseline"
                    )
            elif status == "vcr_only":
                assert not contract_test.exists(), (
                    f"provider '{provider}' is VCR-only in the live baseline but already has a live contract suite; "
                    "promote matrix status before enabling enforcement"
                )
                assert providers[provider]["vcr_cassettes"] == "MUST", (
                    f"provider '{provider}' is VCR-only but the matrix does not require VCR cassettes"
                )
                assert (vcr_dir / provider).is_dir(), (
                    f"provider '{provider}' is VCR-only but {vcr_dir / provider} is missing"
                )
            else:
                pytest.fail(
                    f"unexpected provider_live_api status for '{provider}': {status}"
                )
