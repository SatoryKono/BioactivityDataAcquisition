"""Unit tests for CI quality gate test-health classification."""

from __future__ import annotations

from scripts.engineering.ci.quality_integral_gate import ArchitectureTestStats
from scripts.engineering.ci.quality_integral_gate import (
    TestHealthClassification as HealthClassification,
)
from scripts.engineering.ci.quality_integral_gate import _build_test_health_payload
from scripts.engineering.ci.quality_integral_gate import _classify_test_health

NETWORK_OPT_IN_GATE = "live_network_opt_in_gate"
LIVE_API_GATE_MODE_NON_ALWAYS = "live_api_gate_mode_non_always"
PILOT_PROVIDER_COUNT = "pilot_provider_count"
VCR_ONLY_PROVIDER_COUNT = "vcr_only_provider_count"
CONTRACT_LANE_NOT_RUN = "contract_lane_not_run"
E2E_LANE_NOT_RUN = "e2e_lane_not_run"
MEMORY_LANE_NOT_RUN = "memory_lane_not_run"
ENFORCED_PROVIDERS = "enforced_providers"
LIVE_API_GATE_MODE = "live_api_gate_mode"
NETWORK_OPT_IN_REQUIRED = "network_opt_in_required"
LIVE_API_MINIMUM_BASELINE = "live_api_minimum_baseline"
FIXTURE_GOVERNANCE = "fixture_governance"
CASSETTE_METADATA_PARTIAL = "fixture_governance.cassette_metadata=partial"


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
            NETWORK_OPT_IN_REQUIRED: True,
            LIVE_API_GATE_MODE: "scheduled",
            LIVE_API_MINIMUM_BASELINE: {
                ENFORCED_PROVIDERS: ["chembl", "pubchem"],
                "pilot_providers": ["crossref"],
                "vcr_only_providers": ["openalex"],
            },
        },
        FIXTURE_GOVERNANCE: {"rollout": {"cassette_metadata": "planned"}},
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
        NETWORK_OPT_IN_GATE: 1,
        LIVE_API_GATE_MODE_NON_ALWAYS: 1,
        PILOT_PROVIDER_COUNT: 1,
        VCR_ONLY_PROVIDER_COUNT: 1,
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
            NETWORK_OPT_IN_REQUIRED: False,
            LIVE_API_GATE_MODE: "always",
            LIVE_API_MINIMUM_BASELINE: {
                ENFORCED_PROVIDERS: ["chembl", "pubchem"],
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
    assert CASSETTE_METADATA_PARTIAL in result.reasons
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
            NETWORK_OPT_IN_REQUIRED: False,
            LIVE_API_GATE_MODE: "always",
            LIVE_API_MINIMUM_BASELINE: {
                ENFORCED_PROVIDERS: ["chembl", "pubchem", "uniprot"],
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


def test_classify_test_health_marks_contract_e2e_memory_lanes_as_not_run() -> None:
    """Explicit not-run confidence lanes should keep the result environment-limited."""
    architecture_stats = ArchitectureTestStats(
        tests=80,
        failures=0,
        errors=0,
        skipped=0,
        returncode=0,
    )
    test_matrix = {
        "contract_testing": {
            NETWORK_OPT_IN_REQUIRED: False,
            LIVE_API_GATE_MODE: "always",
            LIVE_API_MINIMUM_BASELINE: {
                ENFORCED_PROVIDERS: ["chembl", "pubchem", "uniprot"],
                "pilot_providers": [],
                "vcr_only_providers": [],
            },
        },
        "test_health_confidence": {
            "lane_absence_skip_classes": [
                {
                    "lane": "contracts",
                    "skip_class": CONTRACT_LANE_NOT_RUN,
                    "reason": "Current quality-gate run does not execute the canonical contracts lane.",
                },
                {
                    "lane": "e2e",
                    "skip_class": E2E_LANE_NOT_RUN,
                    "reason": "Current quality-gate run does not execute the canonical e2e lane.",
                },
                {
                    "lane": "memory",
                    "skip_class": MEMORY_LANE_NOT_RUN,
                    "reason": "Current quality-gate run does not execute the canonical memory lane.",
                },
            ]
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

    assert result.status == "environment_limited_green"
    assert "canonical contracts lane" in " | ".join(result.reasons)
    assert "canonical e2e lane" in " | ".join(result.reasons)
    assert "canonical memory lane" in " | ".join(result.reasons)
    assert dict(result.skip_classes) == {
        CONTRACT_LANE_NOT_RUN: 1,
        E2E_LANE_NOT_RUN: 1,
        MEMORY_LANE_NOT_RUN: 1,
    }


def test_build_test_health_payload_uses_canonical_taxonomy() -> None:
    """Rendered payload should carry canonical labels and merge semantics."""
    classification = HealthClassification(
        status="staged_green",
        summary="Green status is staged.",
        reasons=(CASSETTE_METADATA_PARTIAL,),
        architecture_skip_count=0,
        architecture_skip_ratio=0.0,
        live_contract_enforced_provider_count=4,
        live_contract_pilot_provider_count=1,
        live_contract_vcr_only_provider_count=3,
        skip_classes=(
            (NETWORK_OPT_IN_GATE, 1),
            (LIVE_API_GATE_MODE_NON_ALWAYS, 1),
            (PILOT_PROVIDER_COUNT, 1),
            (VCR_ONLY_PROVIDER_COUNT, 3),
        ),
        staged_rollout_flags=(CASSETTE_METADATA_PARTIAL,),
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
            NETWORK_OPT_IN_GATE: {
                "short_label": "Network Opt-In Gate",
                "definition": "Live tests require explicit network opt-in.",
            },
            LIVE_API_GATE_MODE_NON_ALWAYS: {
                "short_label": "Scheduled Live Gate",
                "definition": "Live execution is not always-on.",
            },
            PILOT_PROVIDER_COUNT: {
                "short_label": "Pilot Providers",
                "definition": "Providers still staged as live pilots.",
            },
            VCR_ONLY_PROVIDER_COUNT: {
                "short_label": "VCR-Only Providers",
                "definition": "Providers still outside live baseline enforcement.",
            },
            CONTRACT_LANE_NOT_RUN: {
                "short_label": "Contracts Lane Not Run",
                "definition": "The canonical contracts lane was not part of this run.",
            },
            E2E_LANE_NOT_RUN: {
                "short_label": "E2E Lane Not Run",
                "definition": "The canonical e2e lane was not part of this run.",
            },
            MEMORY_LANE_NOT_RUN: {
                "short_label": "Memory Lane Not Run",
                "definition": "The canonical memory lane was not part of this run.",
            },
        },
    }

    payload = _build_test_health_payload(classification, taxonomy)

    assert payload["short_label"] == "Staged Green"
    assert payload["definition"] == "Staged confidence surface."
    assert payload["merge_semantics"] == "informational"
    assert payload["merge_blocking_source"] == "ci_pass_fail_and_quality_gate"
    assert payload["skip_classes"] == {
        NETWORK_OPT_IN_GATE: 1,
        LIVE_API_GATE_MODE_NON_ALWAYS: 1,
        PILOT_PROVIDER_COUNT: 1,
        VCR_ONLY_PROVIDER_COUNT: 3,
    }
    assert payload["skip_classes_detail"] == [
        {
            "id": NETWORK_OPT_IN_GATE,
            "count": 1,
            "short_label": "Network Opt-In Gate",
            "definition": "Live tests require explicit network opt-in.",
        },
        {
            "id": LIVE_API_GATE_MODE_NON_ALWAYS,
            "count": 1,
            "short_label": "Scheduled Live Gate",
            "definition": "Live execution is not always-on.",
        },
        {
            "id": PILOT_PROVIDER_COUNT,
            "count": 1,
            "short_label": "Pilot Providers",
            "definition": "Providers still staged as live pilots.",
        },
        {
            "id": VCR_ONLY_PROVIDER_COUNT,
            "count": 3,
            "short_label": "VCR-Only Providers",
            "definition": "Providers still outside live baseline enforcement.",
        },
    ]
