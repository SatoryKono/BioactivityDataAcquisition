#!/usr/bin/env python3
"""Unified entry point for scripts/engineering/qa/ commands.

Usage:
    python -m scripts.engineering.qa <command> [args...]
    python -m scripts.engineering.qa --help

Commands:
    check-naming         Naming convention audit
    check-architecture   Infrastructure architecture compatibility check
    check-app-deps       Application dependency compatibility check
    check-constructor-args Constructor argument compatibility check
    check-c901           C901 complexity baseline enforcement
    check-naming-pkg     Package naming consistency check
    check-exemptions     Quality exemptions audit
    check-docs-drift     Documentation forbidden-pattern drift check
    check-xwalk-missing-backlog Validate xwalk MISSING_* backlog coverage
    validate-dq-consistency Validate DQ policy/config consistency
    check-semantic-field-registry Validate semantic field registry coverage
    check-semantic-registry-drift Validate generated semantic registry drift candidates
    check-semantic-pair-budget Validate semantic pair-matrix drift budgets
    report-semantic-pipeline-audit Generate/check semantic pipeline audit snapshot artifacts
    check-semantic-governance-policy Validate semantic governance policy for reviewed residual semantic debt
    check-semantic-anchor-parity Validate semantic anchor DQ/Gold parity
    check-gold-nullable-numeric Validate Gold nullable numeric compatibility
    check-generic-field-ownership Validate generic semantic field ownership
    check-ontology-unit-semantics Validate ontology/unit role separation
    generate-debt-tasks  Generate architecture debt task backlog from exemptions registry
    reduce-architecture-debt  Build execution plan from latest architecture debt tasks JSON
    check-terminology    Terminology linting
    report-dep-map       Generate/check architecture dependency map
    report-vcr-metadata  Generate/check canonical VCR metadata catalog
    report-provider-contract-drift  Generate provider contract drift diagnostics from replay cassettes
    report-compatibility-importer-census Generate deterministic importer census for sanctioned seams and twin modules
    report-dead-code-inventory Generate repo-local static dead-code review inventory
    report-pubchem-property-vocab Extract observed PubChem property-URN vocabulary
    report-publication-nested-vocab Extract nested publication-sidecar vocabularies
    sync-integration-vcr-policy Sync tracked integration/e2e inventory in integration VCR policy
    report-family-baseline Generate/check RF-06 hotspot-family baseline artifacts
    report-hotspots      Generate hotspot degradation report
    report-duplication-baseline  Generate report-only duplication baseline
    report-function-length-inventory Generate report-only near-threshold function length inventory
    report-normalization-fallback-inventory Generate report-only fallback normalization inventory
    report-chembl-observed-value-inventory Generate/check observed-value inventory from tracked ChEMBL Bronze fixtures
    report-observability-metric-inventory Generate registry/runtime/docs observability metric inventory
    analyze-duplicate-functions Analyze duplicate function names across selected code areas
    calibrate-hotspots   Calibrate hotspot budgets
    run-tests            Run a named test-health lane and emit JUnit/JSON artifacts
    summarize-junit      Aggregate existing JUnit XML into test-health JSON
    test-health          Summarize recent test-health run JSON artifacts
    check-dashboard-visual-semantics Validate Grafana status-panel visual semantic invariants
    report-dashboard-inventory Generate/check dashboard inventory parity plus
        provisioning/deployed drift and health summary
    report-dashboard-query-duplicates Generate report-only exact/near-duplicate Grafana PromQL inventory
"""

from __future__ import annotations

from pathlib import Path

from scripts.engineering.common.cli_dispatch import dispatch_cli, python_command

_TEST_HEALTH_SCRIPT = "test_health.py"

COMMAND_SPECS = {
    "check-naming": "naming_audit.py",
    "check-architecture": "check_architecture.py",
    "check-app-deps": "check_application_deps.py",
    "check-constructor-args": "check_constructor_args.py",
    "check-c901": "check_c901_baseline.py",
    "check-naming-pkg": "check_naming_package_consistency.py",
    "check-exemptions": "check_quality_exemptions.py",
    "check-docs-drift": "check_docs_drift.py",
    "check-xwalk-missing-backlog": "check_xwalk_missing_backlog.py",
    "validate-dq-consistency": "validate_dq_consistency.py",
    "check-semantic-field-registry": "check_semantic_field_registry.py",
    "check-semantic-registry-drift": "check_semantic_registry_drift.py",
    "check-semantic-pair-budget": "check_semantic_pair_matrix_budget.py",
    "report-semantic-pipeline-audit": "generate_semantic_pipeline_audit.py",
    "check-semantic-governance-policy": "check_semantic_governance_policy.py",
    "check-semantic-anchor-parity": "check_semantic_anchor_parity.py",
    "check-gold-nullable-numeric": "check_gold_nullable_numeric_compatibility.py",
    "check-generic-field-ownership": "check_generic_field_ownership.py",
    "check-ontology-unit-semantics": "check_ontology_unit_semantics.py",
    "generate-debt-tasks": "generate_architecture_debt_tasks.py",
    "reduce-architecture-debt": "reduce_architecture_debt.py",
    "check-terminology": "lint_terminology.py",
    "report-dep-map": "generate_architecture_dependency_map.py",
    "report-vcr-metadata": "report_vcr_metadata_catalog.py",
    "report-provider-contract-drift": "report_provider_contract_drift.py",
    "report-compatibility-importer-census": "report_compatibility_importer_census.py",
    "report-dead-code-inventory": "report_dead_code_inventory.py",
    "report-pubchem-property-vocab": "extract_pubchem_property_vocab.py",
    "report-publication-nested-vocab": "extract_publication_nested_vocab.py",
    "sync-integration-vcr-policy": "sync_integration_vcr_policy.py",
    "report-family-baseline": "report_hotspot_family_baseline.py",
    "report-hotspots": "generate_hotspot_degradation_report.py",
    "report-duplication-baseline": "report_duplication_baseline.py",
    "report-function-length-inventory": "report_function_length_inventory.py",
    "report-normalization-fallback-inventory": "report_normalization_fallback_inventory.py",
    "report-chembl-observed-value-inventory": "report_chembl_observed_value_inventory.py",
    "report-observability-metric-inventory": "report_observability_metric_inventory.py",
    "analyze-duplicate-functions": "analyze_duplicate_functions.py",
    "calibrate-hotspots": "calibrate_hotspot_budgets.py",
    "run-tests": python_command(_TEST_HEALTH_SCRIPT, "run-tests"),
    "summarize-junit": python_command(_TEST_HEALTH_SCRIPT, "summarize-junit"),
    "test-health": python_command(_TEST_HEALTH_SCRIPT, "test-health"),
    "check-dashboard-visual-semantics": "check_dashboard_visual_semantics.py",
    "report-dashboard-inventory": "report_dashboard_inventory.py",
    "report-dashboard-query-duplicates": "report_dashboard_query_duplicates.py",
}
COMMAND_SPECS = {
    name: spec if hasattr(spec, "runner") else python_command(spec)
    for name, spec in COMMAND_SPECS.items()
}

_DIR = Path(__file__).parent


def main(argv: list[str] | None = None) -> int:
    return dispatch_cli(
        argv,
        help_text=__doc__ or "",
        commands=COMMAND_SPECS,
        base_dir=_DIR,
    )


if __name__ == "__main__":
    raise SystemExit(main())
