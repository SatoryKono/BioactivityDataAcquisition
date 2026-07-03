"""Architecture tests for bounded contract snapshot governance."""

from __future__ import annotations

import json

import pytest

from tests.architecture._test_matrix_policy_support import ROOT, TESTS_DIR, load_matrix


@pytest.mark.architecture
class TestContractSnapshotGovernance:
    """Validate the bounded live-provider contract snapshot rollout slice."""

    def test_bounded_contract_snapshot_registry_matches_managed_slice(self) -> None:
        matrix = load_matrix()
        fixture_governance = matrix.get("fixture_governance", {})
        registry = fixture_governance.get("contract_snapshot_registry", {})
        providers = registry.get("providers", {})

        assert (
            fixture_governance.get("rollout", {}).get("contract_snapshots")
            == "enforced"
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
