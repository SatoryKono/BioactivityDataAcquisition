"""Architecture tests for contract-testing workflow governance."""

from __future__ import annotations

import pytest

from tests.architecture._test_matrix_policy_support import (
    ROOT,
    TESTS_DIR,
    WORKFLOWS_DIR,
    load_matrix,
)


@pytest.mark.architecture
class TestContractTestingGovernance:
    """Validate contract-testing workflow stays aligned with matrix declarations."""

    def test_contract_testing_matrix_matches_current_workflow_contract(self) -> None:
        matrix = load_matrix()
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
        matrix = load_matrix()
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
