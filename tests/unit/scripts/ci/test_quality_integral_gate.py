"""Unit tests for CI quality gate test-health classification."""

from __future__ import annotations

from scripts.engineering.ci.quality_integral_gate import ArchitectureTestStats
from scripts.engineering.ci.quality_integral_gate import (
    TestHealthClassification as HealthClassification,
)
from scripts.engineering.ci.quality_integral_gate import _build_test_health_payload
from scripts.engineering.ci.quality_integral_gate import _classify_test_health


def test_classify_test_health_environment_limited_green() -> None:
    """Skip- and provider-gated confidence should be environment-limited."""
    architecture_stats = ArchitectureTestStats(
        tests=120,
        failures=0,
        errors=0,
        skipped=12,
        returncode=0,
    )
    test_matrix = {
        "contract_testing": {
            "network_opt_in_required": True,
            "live_api_gate_mode": "scheduled",
            "live_api_minimum_baseline": {
                "enforced_providers": ["chembl", "pubchem"],
                "pilot_providers": ["crossref"],
                "vcr_only_providers": ["openalex"],
            },
        },
        "fixture_governance": {"rollout": {"cassette_metadata": "planned"}},
    }

    result = _classify_test_health(
        architecture_stats,
        test_matrix,
        suite_green=True,
    )

    assert result.status == "environment_limited_green"
    assert "network opt-in gated" in " | ".join(result.reasons)
    assert "pilot provider" in " | ".join(result.reasons)
    assert result.architecture_skip_count == 12
    assert result.live_contract_pilot_provider_count == 1
    assert result.live_contract_vcr_only_provider_count == 1
    assert dict(result.skip_classes) == {
        "architecture_suite_skips": 12,
        "live_network_opt_in_gate": 1,
        "live_api_gate_mode_non_always": 1,
        "pilot_provider_count": 1,
        "vcr_only_provider_count": 1,
    }


def test_classify_test_health_staged_green() -> None:
    """Policy staging without environment gating should be staged green."""
    architecture_stats = ArchitectureTestStats(
        tests=50,
        failures=0,
        errors=0,
        skipped=0,
        returncode=0,
    )
    test_matrix = {
        "contract_testing": {
            "network_opt_in_required": False,
            "live_api_gate_mode": "always",
            "live_api_minimum_baseline": {
                "enforced_providers": ["chembl", "pubchem"],
                "pilot_providers": [],
                "vcr_only_providers": [],
            },
        },
        "fixture_governance": {
            "rollout": {
                "cassette_metadata": "partial",
                "golden_masters": "enforced",
            }
        },
        "mutation_testing": {
            "ci_gate_mode": "partial",
            "targets": {
                "domain": {"enforced": True},
                "application": {"enforced": False},
            },
        },
    }

    result = _classify_test_health(
        architecture_stats,
        test_matrix,
        suite_green=True,
    )

    assert result.status == "staged_green"
    assert "fixture_governance.cassette_metadata=partial" in result.reasons
    assert "mutation_testing.ci_gate_mode=partial" in result.reasons


def test_classify_test_health_fully_exercised_green() -> None:
    """No staged or environment markers should yield fully exercised green."""
    architecture_stats = ArchitectureTestStats(
        tests=80,
        failures=0,
        errors=0,
        skipped=0,
        returncode=0,
    )
    test_matrix = {
        "contract_testing": {
            "network_opt_in_required": False,
            "live_api_gate_mode": "always",
            "live_api_minimum_baseline": {
                "enforced_providers": ["chembl", "pubchem", "uniprot"],
                "pilot_providers": [],
                "vcr_only_providers": [],
            },
        },
        "fixture_governance": {
            "rollout": {
                "cassette_metadata": "enforced",
                "cassette_metadata_catalog": "enforced",
            }
        },
        "mutation_testing": {
            "ci_gate_mode": "full",
            "targets": {
                "domain": {"enforced": True},
                "application": {"enforced": True},
            },
        },
    }

    result = _classify_test_health(
        architecture_stats,
        test_matrix,
        suite_green=True,
    )

    assert result.status == "fully_exercised_green"
    assert result.reasons == ()
    assert result.skip_classes == ()
    assert result.staged_rollout_flags == ()


def test_build_test_health_payload_uses_canonical_taxonomy() -> None:
    """Rendered payload should carry canonical labels and merge semantics."""
    classification = HealthClassification(
        status="staged_green",
        summary="Green status is staged.",
        reasons=("fixture_governance.cassette_metadata=partial",),
        architecture_skip_count=0,
        architecture_skip_ratio=0.0,
        live_contract_enforced_provider_count=4,
        live_contract_pilot_provider_count=1,
        live_contract_vcr_only_provider_count=3,
        skip_classes=(
            ("live_network_opt_in_gate", 1),
            ("live_api_gate_mode_non_always", 1),
            ("pilot_provider_count", 1),
            ("vcr_only_provider_count", 3),
        ),
        staged_rollout_flags=("fixture_governance.cassette_metadata=partial",),
    )
    taxonomy = {
        "classification_mode": "informational",
        "merge_blocking_source": "ci_pass_fail_and_quality_gate",
        "merge_blocking_note": "Descriptive only.",
        "statuses": {
            "staged_green": {
                "short_label": "Staged Green",
                "definition": "Staged confidence surface.",
                "merge_semantics": "informational",
            }
        },
        "skip_classes": {
            "live_network_opt_in_gate": {
                "short_label": "Network Opt-In Gate",
                "definition": "Live tests require explicit network opt-in.",
            },
            "live_api_gate_mode_non_always": {
                "short_label": "Scheduled Live Gate",
                "definition": "Live execution is not always-on.",
            },
            "pilot_provider_count": {
                "short_label": "Pilot Providers",
                "definition": "Providers still staged as live pilots.",
            },
            "vcr_only_provider_count": {
                "short_label": "VCR-Only Providers",
                "definition": "Providers still outside live baseline enforcement.",
            },
        },
    }

    payload = _build_test_health_payload(classification, taxonomy)

    assert payload["short_label"] == "Staged Green"
    assert payload["definition"] == "Staged confidence surface."
    assert payload["merge_semantics"] == "informational"
    assert payload["merge_blocking_source"] == "ci_pass_fail_and_quality_gate"
    assert payload["skip_classes"] == {
        "live_network_opt_in_gate": 1,
        "live_api_gate_mode_non_always": 1,
        "pilot_provider_count": 1,
        "vcr_only_provider_count": 3,
    }
    assert payload["skip_classes_detail"] == [
        {
            "id": "live_network_opt_in_gate",
            "count": 1,
            "short_label": "Network Opt-In Gate",
            "definition": "Live tests require explicit network opt-in.",
        },
        {
            "id": "live_api_gate_mode_non_always",
            "count": 1,
            "short_label": "Scheduled Live Gate",
            "definition": "Live execution is not always-on.",
        },
        {
            "id": "pilot_provider_count",
            "count": 1,
            "short_label": "Pilot Providers",
            "definition": "Providers still staged as live pilots.",
        },
        {
            "id": "vcr_only_provider_count",
            "count": 3,
            "short_label": "VCR-Only Providers",
            "definition": "Providers still outside live baseline enforcement.",
        },
    ]
