"""Unit tests for CI quality gate test-health classification."""

from __future__ import annotations

import pytest

from types import SimpleNamespace

from scripts.engineering.ci.quality_integral_gate import ArchitectureTestStats
from scripts.engineering.ci.quality_integral_gate import QualityGateOutputContext
from scripts.engineering.ci.quality_integral_gate import (
    TestHealthClassification as HealthClassification,
)
from scripts.engineering.ci.quality_integral_gate import _build_test_health_payload
from scripts.engineering.ci.quality_integral_gate import _classify_test_health
from scripts.engineering.ci.quality_integral_gate import _quality_gate_output
from scripts.engineering.ci.quality_integral_gate import _summary_lines

pytestmark = pytest.mark.unit

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


def test_classify_test_health_blocks_zero_debt_environment_gaps() -> None:
    """Zero-debt architecture and provider gaps should block green."""
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

    assert result.status == "non_green"
    assert "architecture skip budget is zero" in " | ".join(result.reasons)
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


def test_classify_test_health_blocks_missing_contract_e2e_memory_lanes() -> None:
    """Explicit not-run confidence lanes should block green."""
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
                    "reason": (
                        "Current quality-integral gate slice runs architecture "
                        "checks only; the dedicated CI memory-tests lane remains "
                        "separate."
                    ),
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

    assert result.status == "non_green"
    assert "canonical contracts lane" in " | ".join(result.reasons)
    assert "canonical e2e lane" in " | ".join(result.reasons)
    assert "dedicated CI memory-tests lane remains separate" in " | ".join(
        result.reasons
    )
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
                "definition": (
                    "The dedicated CI memory-tests lane is tracked outside this "
                    "quality-integral gate slice."
                ),
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


def test_quality_gate_output_and_summary_include_debt_governance_surface() -> None:
    """Quality gate payloads should publish the unified debt-governance snapshot."""

    class _FakeCompatibilitySurface:
        def __init__(self) -> None:
            self.curated_inventory_rows = 14
            self.measured_tracked_modules = 14
            self.measured_only_modules = 0
            self.deprecated_warn_modules = 0
            self.compat_shim_modules = 0
            self.mixed_modules = 0
            self.retained_entrypoints = 1
            self.public_entrypoints = 13

        def as_dict(self) -> dict[str, int]:
            return {
                "curated_inventory_rows": self.curated_inventory_rows,
                "measured_tracked_modules": self.measured_tracked_modules,
                "measured_only_modules": self.measured_only_modules,
                "deprecated_warn_modules": self.deprecated_warn_modules,
                "compat_shim_modules": self.compat_shim_modules,
                "mixed_modules": self.mixed_modules,
                "retained_entrypoints": self.retained_entrypoints,
                "public_entrypoints": self.public_entrypoints,
            }

    class _FakeDebtGovernanceSurface:
        def __init__(self) -> None:
            self.compatibility_surface = _FakeCompatibilitySurface()
            self.runtime_uuid = SimpleNamespace(
                runtime_uuid_seam_count=14,
                replay_critical_uuid_seam_count=0,
            )
            self.retirement = SimpleNamespace(
                triaged_entry_count=19,
                repo_wide_zero_import_candidate_count=45,
                repo_wide_classified_zero_import_candidate_count=45,
                repo_wide_untriaged_zero_import_candidate_count=0,
            )
            self.test_governance = SimpleNamespace(
                compatibility_test_files=53,
                refined_assertless_tests=499,
                markerless_test_functions=6991,
                duplicate_test_names=787,
                duplicate_test_name_occurrences=869,
                uuid4_call_sites=400,
                date_today_call_sites=0,
            )

        def as_dict(self) -> dict[str, object]:
            return {
                "compatibility_surface": self.compatibility_surface.as_dict(),
                "runtime_uuid": {
                    "runtime_uuid_seam_count": self.runtime_uuid.runtime_uuid_seam_count,
                    "replay_critical_uuid_seam_count": (
                        self.runtime_uuid.replay_critical_uuid_seam_count
                    ),
                },
                "retirement": {
                    "triaged_entry_count": self.retirement.triaged_entry_count,
                    "repo_wide_zero_import_candidate_count": (
                        self.retirement.repo_wide_zero_import_candidate_count
                    ),
                    "repo_wide_classified_zero_import_candidate_count": (
                        self.retirement.repo_wide_classified_zero_import_candidate_count
                    ),
                    "repo_wide_untriaged_zero_import_candidate_count": (
                        self.retirement.repo_wide_untriaged_zero_import_candidate_count
                    ),
                },
                "test_governance": {
                    "compatibility_test_files": (
                        self.test_governance.compatibility_test_files
                    ),
                    "refined_assertless_tests": (
                        self.test_governance.refined_assertless_tests
                    ),
                    "markerless_test_functions": (
                        self.test_governance.markerless_test_functions
                    ),
                    "duplicate_test_names": (self.test_governance.duplicate_test_names),
                    "duplicate_test_name_occurrences": (
                        self.test_governance.duplicate_test_name_occurrences
                    ),
                    "uuid4_call_sites": self.test_governance.uuid4_call_sites,
                    "date_today_call_sites": self.test_governance.date_today_call_sites,
                },
            }

    compatibility_surface = _FakeCompatibilitySurface()
    debt_governance_surface = _FakeDebtGovernanceSurface()
    test_health_payload = {
        "short_label": "Fully Exercised Green",
        "definition": "No staged caveats remain.",
        "merge_semantics": "blocking",
        "merge_blocking_source": "ci_pass_fail_and_quality_gate",
        "skip_classes_detail": [],
    }
    test_health = HealthClassification(
        status="fully_exercised_green",
        summary="All confidence lanes green.",
        reasons=(),
        architecture_skip_count=0,
        architecture_skip_ratio=0.0,
        live_contract_enforced_provider_count=3,
        live_contract_pilot_provider_count=0,
        live_contract_vcr_only_provider_count=0,
        skip_classes=(),
        staged_rollout_flags=(),
    )

    output = _quality_gate_output(
        QualityGateOutputContext(
            quarter="2026-Q2",
            architecture_stats=ArchitectureTestStats(
                tests=10,
                failures=0,
                errors=0,
                skipped=0,
                returncode=0,
            ),
            max_total_exemptions=12,
            min_integral_score=70.0,
            ci_target={
                "architecture_test_failures_max": 0,
                "total_exemptions_max": 12,
                "max_class_loc_max": 300,
                "domain_cc_gt5_exemptions_max": 0,
                "vcr_cassettes_min_per_provider": 20,
                "ruff_formatting_violations_max": 0,
                "coverage_threshold_percent": 85.0,
            },
            arch_failures=0,
            total_exemptions=2,
            max_class_loc=200,
            domain_cc_exemptions=0,
            min_provider_vcr=20,
            provider_vcr_counts={"chembl": 20},
            ruff_violations=0,
            coverage_percent=90.0,
            compatibility_surface=compatibility_surface,
            debt_governance_surface=debt_governance_surface,
            architecture_quality_scorecard={
                "schema_version": 1,
                "integral_score": 7.98,
                "categories": [],
            },
            test_health_payload=test_health_payload,
            bonus=5.0,
            summary=SimpleNamespace(integral_score=72.0),
            adjusted_integral_score=77.0,
            gate_pass=True,
            violations=[],
        )
    )

    assert "debt_governance_surface" in output
    assert output["architecture_quality_scorecard"]["integral_score"] == 7.98
    assert (
        output["debt_governance_surface"]["runtime_uuid"]["runtime_uuid_seam_count"]
        == 14
    )

    summary = _summary_lines(
        quarter="2026-Q2",
        adjusted_integral_score=77.0,
        min_integral_score=70.0,
        arch_failures=0,
        test_health=test_health,
        test_health_payload=test_health_payload,
        total_exemptions=2,
        compatibility_surface=compatibility_surface,
        debt_governance_surface=debt_governance_surface,
    )

    rendered = "\n".join(summary)
    assert "## Debt Governance Surface Snapshot" in rendered
    assert "- runtime_uuid_seam_count: `14`" in rendered
    assert "- triaged_entry_count: `19`" in rendered
    assert "- compatibility_test_files: `53`" in rendered
