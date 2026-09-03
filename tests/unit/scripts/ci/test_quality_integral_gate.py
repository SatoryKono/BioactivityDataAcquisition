# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for CI quality gate test-health classification."""

from __future__ import annotations

from pathlib import Path

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


def _fake_compatibility_surface() -> SimpleNamespace:
    payload = {
        "curated_inventory_rows": 14,
        "measured_tracked_modules": 14,
        "measured_only_modules": 0,
        "deprecated_warn_modules": 0,
        "compat_shim_modules": 0,
        "mixed_modules": 0,
        "retained_entrypoints": 1,
        "public_entrypoints": 13,
    }
    return SimpleNamespace(**payload, as_dict=lambda: dict(payload))


def _fake_debt_governance_surface() -> SimpleNamespace:
    compatibility_surface = _fake_compatibility_surface()
    runtime_uuid = SimpleNamespace(
        runtime_uuid_seam_count=14,
        replay_critical_uuid_seam_count=0,
    )
    retirement = SimpleNamespace(
        triaged_entry_count=18,
        repo_wide_zero_import_candidate_count=2,
        repo_wide_classified_zero_import_candidate_count=2,
        repo_wide_untriaged_zero_import_candidate_count=0,
        repo_wide_owner_test_anchored_candidate_count=2,
        repo_wide_candidates_without_owner_tests_count=0,
        repo_wide_non_static_reachability_candidate_count=2,
        triaged_retained_owner_test_anchored_count=14,
        triaged_retained_without_owner_tests_count=0,
    )
    test_governance = SimpleNamespace(
        compatibility_test_files=32,
        refined_assertless_tests=0,
        markerless_test_functions=0,
        duplicate_test_names=0,
        duplicate_test_name_occurrences=0,
        uuid4_call_sites=0,
        date_today_call_sites=0,
    )
    return SimpleNamespace(
        compatibility_surface=compatibility_surface,
        runtime_uuid=runtime_uuid,
        retirement=retirement,
        test_governance=test_governance,
        as_dict=lambda: {
            "compatibility_surface": compatibility_surface.as_dict(),
            "runtime_uuid": {
                "runtime_uuid_seam_count": runtime_uuid.runtime_uuid_seam_count,
                "replay_critical_uuid_seam_count": (
                    runtime_uuid.replay_critical_uuid_seam_count
                ),
            },
            "retirement": {
                "triaged_entry_count": retirement.triaged_entry_count,
                "repo_wide_zero_import_candidate_count": (
                    retirement.repo_wide_zero_import_candidate_count
                ),
                "repo_wide_classified_zero_import_candidate_count": (
                    retirement.repo_wide_classified_zero_import_candidate_count
                ),
                "repo_wide_untriaged_zero_import_candidate_count": (
                    retirement.repo_wide_untriaged_zero_import_candidate_count
                ),
                "repo_wide_owner_test_anchored_candidate_count": (
                    retirement.repo_wide_owner_test_anchored_candidate_count
                ),
                "repo_wide_candidates_without_owner_tests_count": (
                    retirement.repo_wide_candidates_without_owner_tests_count
                ),
                "repo_wide_non_static_reachability_candidate_count": (
                    retirement.repo_wide_non_static_reachability_candidate_count
                ),
                "triaged_retained_owner_test_anchored_count": (
                    retirement.triaged_retained_owner_test_anchored_count
                ),
                "triaged_retained_without_owner_tests_count": (
                    retirement.triaged_retained_without_owner_tests_count
                ),
            },
            "test_governance": {
                "compatibility_test_files": test_governance.compatibility_test_files,
                "refined_assertless_tests": test_governance.refined_assertless_tests,
                "markerless_test_functions": (
                    test_governance.markerless_test_functions
                ),
                "duplicate_test_names": test_governance.duplicate_test_names,
                "duplicate_test_name_occurrences": (
                    test_governance.duplicate_test_name_occurrences
                ),
                "uuid4_call_sites": test_governance.uuid4_call_sites,
                "date_today_call_sites": test_governance.date_today_call_sites,
            },
        },
    )


def _fully_exercised_test_health_payload() -> dict[str, object]:
    return {
        "short_label": "Fully Exercised Green",
        "definition": "No staged caveats remain.",
        "merge_semantics": "blocking",
        "merge_blocking_source": "ci_pass_fail_and_quality_gate",
        "skip_classes_detail": [],
    }


def _fully_exercised_test_health() -> HealthClassification:
    return HealthClassification(
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


def _quality_gate_context_with_debt_surface() -> QualityGateOutputContext:
    compatibility_surface = _fake_compatibility_surface()
    return QualityGateOutputContext(
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
        debt_governance_surface=_fake_debt_governance_surface(),
        architecture_quality_scorecard={
            "schema_version": 1,
            "integral_score": 7.98,
            "categories": [],
        },
        test_health_payload=_fully_exercised_test_health_payload(),
        bonus=5.0,
        summary=SimpleNamespace(integral_score=72.0),
        adjusted_integral_score=77.0,
        gate_pass=True,
        violations=[],
    )


def test_quality_gate_output_includes_debt_governance_surface() -> None:
    """Quality gate output should publish the unified debt-governance snapshot."""
    output = _quality_gate_output(_quality_gate_context_with_debt_surface())

    assert "debt_governance_surface" in output
    assert output["architecture_quality_scorecard"]["integral_score"] == 7.98
    assert (
        output["debt_governance_surface"]["runtime_uuid"]["runtime_uuid_seam_count"]
        == 14
    )


def test_summary_lines_include_debt_governance_surface() -> None:
    """Rendered summary should include the debt-governance snapshot section."""
    context = _quality_gate_context_with_debt_surface()
    summary = _summary_lines(
        quarter=context.quarter,
        adjusted_integral_score=context.adjusted_integral_score,
        min_integral_score=context.min_integral_score,
        arch_failures=0,
        test_health=_fully_exercised_test_health(),
        test_health_payload=_fully_exercised_test_health_payload(),
        total_exemptions=context.total_exemptions,
        compatibility_surface=context.compatibility_surface,
        debt_governance_surface=context.debt_governance_surface,
    )

    rendered = "\n".join(summary)
    assert "## Debt Governance Surface Snapshot" in rendered
    assert "- runtime_uuid_seam_count: `14`" in rendered
    assert "- triaged_entry_count: `18`" in rendered
    assert "- repo_wide_owner_test_anchored_candidate_count: `2`" in rendered
    assert "- compatibility_test_files: `32`" in rendered


def test_resolve_architecture_stats_external_owner_skips_pytest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from argparse import Namespace

    from scripts.engineering.ci.quality_integral_gate import (
        _resolve_architecture_stats,
    )

    def _fail(_path: str) -> None:
        raise AssertionError("architecture pytest must not run for workflow owner")

    monkeypatch.setattr(
        "scripts.engineering.ci.quality_integral_gate._run_architecture_tests",
        _fail,
    )
    stats = _resolve_architecture_stats(
        Namespace(
            architecture_owner="lint-architecture-workflow",
            architecture_tests="tests/architecture",
        )
    )
    assert stats.owner == "lint-architecture-workflow"
    assert stats.tests == 0
    assert stats.failures == 0
    assert stats.skipped == 0


def test_architecture_junit_skips_fails_on_empty_and_skipped(tmp_path: Path) -> None:
    from scripts.engineering.ci.check_architecture_junit_skips import main as skips_main

    empty = tmp_path / "empty"
    empty.mkdir()
    import sys

    old = sys.argv
    sys.argv = ["prog", "--junit-dir", str(empty)]
    try:
        assert skips_main() == 1
        xml_dir = tmp_path / "junit"
        xml_dir.mkdir()
        skipped_xml = (
            '<testsuite tests="2" skipped="1" failures="0" errors="0"></testsuite>'
        )
        (xml_dir / "suite.xml").write_text(skipped_xml + chr(10), encoding="utf-8")
        sys.argv = ["prog", "--junit-dir", str(xml_dir)]
        assert skips_main() == 1
        ok_xml = '<testsuite tests="2" skipped="0" failures="0" errors="0"></testsuite>'
        (xml_dir / "suite.xml").write_text(ok_xml + chr(10), encoding="utf-8")
        sys.argv = ["prog", "--junit-dir", str(xml_dir)]
        assert skips_main() == 0
    finally:
        sys.argv = old
