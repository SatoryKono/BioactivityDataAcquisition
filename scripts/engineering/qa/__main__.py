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
    check-duplication-complexity-exemptions Validate duplication/complexity exemption registry
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
    check-vcr-replay-preflight  Fail fast on unresolved replay VCR pointers
    report-provider-contract-drift  Generate provider contract drift diagnostics from replay cassettes
    report-compatibility-importer-census Generate deterministic importer census for sanctioned seams and twin modules
    report-pipeline-config-contract-ownership-map Generate/check pipeline-config-contract ownership traces
    report-contract-coverage-matrix Generate/check contract coverage matrix for active entity configs
    report-domain-io-taint-inventory Generate/check semantic Domain I/O taint inventory
    report-port-adapter-factory-coverage Generate/check core port-adapter-factory coverage matrix
    report-module-coverage Generate/check module-level coverage inventory
    check-branch-coverage Enforce branch coverage from reports/coverage/coverage.xml
    report-dead-code-inventory Generate repo-local static dead-code review inventory
    report-pubchem-property-vocab Extract observed PubChem property-URN vocabulary
    report-publication-nested-vocab Extract nested publication-sidecar vocabularies
    sync-integration-vcr-policy Sync tracked integration/e2e inventory in integration VCR policy
    report-family-baseline Generate/check RF-06 hotspot-family baseline artifacts
    report-hotspots      Generate hotspot degradation report
    report-duplication-baseline  Generate report-only duplication baseline
    report-artifact-duplication-audit  Generate/check JSCPD-excluded governance artifact duplication audit
    report-function-length-inventory Generate report-only near-threshold function length inventory
    report-normalization-fallback-inventory Generate report-only fallback normalization inventory
    report-chembl-observed-value-inventory Generate/check observed-value inventory from tracked ChEMBL Bronze fixtures
    report-observability-metric-inventory Generate registry/runtime/docs observability metric inventory
    report-adr-enforcement-matrix Generate/check accepted ADR enforcement coverage matrix
    report-invariant-audit-rebaseline Generate/check stale invariant-audit rebaseline matrix
    report-architecture-debt-remote-main-baseline Generate/check clean remote-main architecture debt baseline
    report-debt-governance-gates Generate/check debt-reduction fail-fast gate rollup
    run-architecture-audit-read-only Run check-only architecture evidence diagnostics
    analyze-duplicate-functions Analyze duplicate function names across selected code areas
    calibrate-hotspots   Calibrate hotspot budgets
    run-tests            Run a named test-health lane and emit JUnit/JSON artifacts
    summarize-junit      Aggregate existing JUnit XML into test-health JSON
    test-health          Summarize recent test-health run JSON artifacts
    check-dashboard-visual-semantics Validate Grafana status-panel visual semantic invariants
    check-prometheus-rules Validate Prometheus rules with deterministic promtool preflight
    report-dashboard-inventory Generate/check dashboard inventory parity plus
        provisioning/deployed drift and health summary
    report-dashboard-panel-audit-matrix Generate/check dashboard panel audit matrix
    report-panel-title-inventory Generate/check generated dashboard panel-title inventory mirror
    report-dashboard-query-duplicates Generate report-only exact/near-duplicate Grafana PromQL inventory
    report-dashboard-promql-scope Generate/check dashboard PromQL scope and forbidden-label inventory
    run-observability-closure-campaign Run the bounded 15-pipeline observability closure campaign
"""

from __future__ import annotations

from scripts.engineering.common.cli_dispatch import dispatch_cli, module_command

COMMAND_MODULES: dict[str, str] = {
    "check-naming": "scripts.engineering.qa.naming_audit",
    "check-architecture": "scripts.engineering.qa.check_architecture",
    "check-app-deps": "scripts.engineering.qa.check_application_deps",
    "check-constructor-args": "scripts.engineering.qa.check_constructor_args",
    "check-duplication-complexity-exemptions": (
        "scripts.engineering.qa.check_duplication_complexity_exemptions"
    ),
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
    "check-vcr-replay-preflight": (
        "scripts.engineering.qa.vcr.check_replay_preflight"
    ),
    "report-provider-contract-drift": "scripts.engineering.qa.report_provider_contract_drift",
    "report-compatibility-importer-census": "scripts.engineering.qa.report_compatibility_importer_census",
    "report-pipeline-config-contract-ownership-map": "scripts.engineering.qa.report_pipeline_config_contract_ownership",
    "report-contract-coverage-matrix": "scripts.engineering.qa.report_contract_coverage_matrix",
    "report-domain-io-taint-inventory": (
        "scripts.engineering.qa.report_domain_io_taint_inventory"
    ),
    "report-port-adapter-factory-coverage": (
        "scripts.engineering.qa.report_port_adapter_factory_coverage"
    ),
    "report-module-coverage": "scripts.engineering.qa.report_module_coverage_inventory",
    "check-branch-coverage": "scripts.engineering.qa.check_branch_coverage",
    "report-dead-code-inventory": "scripts.engineering.qa.report_dead_code_inventory",
    "report-pubchem-property-vocab": "scripts.engineering.qa.extract_pubchem_property_vocab",
    "report-publication-nested-vocab": "scripts.engineering.qa.extract_publication_nested_vocab",
    "sync-integration-vcr-policy": "scripts.engineering.qa.sync_integration_vcr_policy",
    "report-family-baseline": "scripts.engineering.qa.report_hotspot_family_baseline",
    "report-hotspots": "scripts.engineering.qa.generate_hotspot_degradation_report",
    "report-duplication-baseline": "scripts.engineering.qa.report_duplication_baseline",
    "report-artifact-duplication-audit": (
        "scripts.engineering.qa.report_artifact_duplication_audit"
    ),
    "report-function-length-inventory": "scripts.engineering.qa.report_function_length_inventory",
    "report-normalization-fallback-inventory": "scripts.engineering.qa.report_normalization_fallback_inventory",
    "report-chembl-observed-value-inventory": "scripts.engineering.qa.report_chembl_observed_value_inventory",
    "report-observability-metric-inventory": "scripts.engineering.qa.report_observability_metric_inventory",
    "report-adr-enforcement-matrix": "scripts.engineering.qa.report_adr_enforcement_matrix",
    "report-invariant-audit-rebaseline": (
        "scripts.engineering.qa.report_invariant_audit_rebaseline"
    ),
    "report-architecture-debt-remote-main-baseline": (
        "scripts.engineering.qa.report_architecture_debt_remote_main_baseline"
    ),
    "report-debt-governance-gates": "scripts.engineering.qa.report_debt_governance_gates",
    "run-architecture-audit-read-only": (
        "scripts.engineering.qa.run_architecture_audit_read_only"
    ),
    "analyze-duplicate-functions": "scripts.engineering.qa.analyze_duplicate_functions",
    "calibrate-hotspots": "scripts.engineering.qa.calibrate_hotspot_budgets",
    "check-dashboard-visual-semantics": "scripts.engineering.qa.check_dashboard_visual_semantics",
    "check-prometheus-rules": "scripts.engineering.qa.check_prometheus_rules",
    "report-dashboard-inventory": "scripts.engineering.qa.report_dashboard_inventory",
    "report-dashboard-query-duplicates": "scripts.engineering.qa.report_dashboard_query_duplicates",
    "report-dashboard-promql-scope": "scripts.engineering.qa.report_dashboard_promql_scope",
    "report-dashboard-panel-audit-matrix": (
        "scripts.engineering.qa.report_dashboard_panel_audit_matrix"
    ),
    "report-panel-title-inventory": (
        "scripts.engineering.qa.report_panel_title_inventory"
    ),
    "run-observability-closure-campaign": (
        "scripts.engineering.qa.run_observability_closure_campaign"
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
