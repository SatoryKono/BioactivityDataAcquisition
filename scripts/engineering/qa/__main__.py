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
    report-pipeline-config-contract-ownership-map Generate/check pipeline-config-contract ownership traces
    report-contract-coverage-matrix Generate/check contract coverage matrix for active entity configs
    report-module-coverage Generate/check module-level coverage inventory
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
    report-adr-enforcement-matrix Generate/check accepted ADR enforcement coverage matrix
    report-architecture-debt-remote-main-baseline Generate/check clean remote-main architecture debt baseline
    report-debt-governance-gates Generate/check debt-reduction fail-fast gate rollup
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

from scripts.engineering.common.cli_dispatch import dispatch_cli, module_command

COMMAND_MODULES: dict[str, str] = {
    "check-naming": "scripts.engineering.qa.naming_audit",
    "check-architecture": "scripts.engineering.qa.check_architecture",
    "check-app-deps": "scripts.engineering.qa.check_application_deps",
    "check-constructor-args": "scripts.engineering.qa.check_constructor_args",
    "check-c901": "scripts.engineering.qa.check_c901_baseline",
    "check-naming-pkg": "scripts.engineering.qa.check_naming_package_consistency",
    "check-exemptions": "scripts.engineering.qa.check_quality_exemptions",
    "check-docs-drift": "scripts.engineering.qa.check_docs_drift",
    "check-xwalk-missing-backlog": "scripts.engineering.qa.check_xwalk_missing_backlog",
    "validate-dq-consistency": "scripts.engineering.qa.validate_dq_consistency",
    "check-semantic-field-registry": "scripts.engineering.qa.check_semantic_field_registry",
    "check-semantic-registry-drift": "scripts.engineering.qa.check_semantic_registry_drift",
    "check-semantic-pair-budget": "scripts.engineering.qa.check_semantic_pair_matrix_budget",
    "report-semantic-pipeline-audit": "scripts.engineering.qa.generate_semantic_pipeline_audit",
    "check-semantic-governance-policy": "scripts.engineering.qa.check_semantic_governance_policy",
    "check-semantic-anchor-parity": "scripts.engineering.qa.check_semantic_anchor_parity",
    "check-gold-nullable-numeric": "scripts.engineering.qa.check_gold_nullable_numeric_compatibility",
    "check-generic-field-ownership": "scripts.engineering.qa.check_generic_field_ownership",
    "check-ontology-unit-semantics": "scripts.engineering.qa.check_ontology_unit_semantics",
    "generate-debt-tasks": "scripts.engineering.qa.generate_architecture_debt_tasks",
    "reduce-architecture-debt": "scripts.engineering.qa.reduce_architecture_debt",
    "check-terminology": "scripts.engineering.qa.lint_terminology",
    "report-dep-map": "scripts.engineering.qa.generate_architecture_dependency_map",
    "report-vcr-metadata": "scripts.engineering.qa.report_vcr_metadata_catalog",
    "report-provider-contract-drift": "scripts.engineering.qa.report_provider_contract_drift",
    "report-compatibility-importer-census": "scripts.engineering.qa.report_compatibility_importer_census",
    "report-pipeline-config-contract-ownership-map": "scripts.engineering.qa.report_pipeline_config_contract_ownership",
    "report-contract-coverage-matrix": "scripts.engineering.qa.report_contract_coverage_matrix",
    "report-module-coverage": "scripts.engineering.qa.report_module_coverage_inventory",
    "report-dead-code-inventory": "scripts.engineering.qa.report_dead_code_inventory",
    "report-pubchem-property-vocab": "scripts.engineering.qa.extract_pubchem_property_vocab",
    "report-publication-nested-vocab": "scripts.engineering.qa.extract_publication_nested_vocab",
    "sync-integration-vcr-policy": "scripts.engineering.qa.sync_integration_vcr_policy",
    "report-family-baseline": "scripts.engineering.qa.report_hotspot_family_baseline",
    "report-hotspots": "scripts.engineering.qa.generate_hotspot_degradation_report",
    "report-duplication-baseline": "scripts.engineering.qa.report_duplication_baseline",
    "report-function-length-inventory": "scripts.engineering.qa.report_function_length_inventory",
    "report-normalization-fallback-inventory": "scripts.engineering.qa.report_normalization_fallback_inventory",
    "report-chembl-observed-value-inventory": "scripts.engineering.qa.report_chembl_observed_value_inventory",
    "report-observability-metric-inventory": "scripts.engineering.qa.report_observability_metric_inventory",
    "report-adr-enforcement-matrix": "scripts.engineering.qa.report_adr_enforcement_matrix",
    "report-architecture-debt-remote-main-baseline": (
        "scripts.engineering.qa.report_architecture_debt_remote_main_baseline"
    ),
    "report-debt-governance-gates": "scripts.engineering.qa.report_debt_governance_gates",
    "analyze-duplicate-functions": "scripts.engineering.qa.analyze_duplicate_functions",
    "calibrate-hotspots": "scripts.engineering.qa.calibrate_hotspot_budgets",
    "check-dashboard-visual-semantics": "scripts.engineering.qa.check_dashboard_visual_semantics",
    "report-dashboard-inventory": "scripts.engineering.qa.report_dashboard_inventory",
    "report-dashboard-query-duplicates": "scripts.engineering.qa.report_dashboard_query_duplicates",
    "report-dashboard-panel-audit-matrix": (
        "scripts.engineering.qa.report_dashboard_panel_audit_matrix"
    ),
}
COMMAND_SPECS = {
    name: module_command(module) for name, module in COMMAND_MODULES.items()
}
COMMAND_SPECS.update(
    {
        "run-tests": module_command("scripts.engineering.qa.test_health", "run-tests"),
        "summarize-junit": module_command(
            "scripts.engineering.qa.test_health", "summarize-junit"
        ),
        "test-health": module_command(
            "scripts.engineering.qa.test_health", "test-health"
        ),
    }
)


def main(argv: list[str] | None = None) -> int:
    return dispatch_cli(
        argv,
        help_text=__doc__ or "",
        commands=COMMAND_SPECS,
    )


if __name__ == "__main__":
    raise SystemExit(main())
