#!/usr/bin/env python3
"""Unified entry point for scripts/schema/ commands.

Usage:
    python -m scripts.schema <command> [args...]
    python -m scripts.schema --help

Commands:
    check-invariants       Validate config CI invariants (naming, schemas, auth, keys)
    check-required-fields  Validate silver required_fields cover YAML requiredness
    audit-optionality      Audit/check effective_optional_v1 resolved from config surface
    check-config-paths     Check for legacy dq/filter config path references
    generate-pipeline      Generate pipeline JSON schema
    generate-artifacts     Generate schema artifacts
    generate-pubtype       Generate publication type classification artifacts
    generate-contracts     Generate contracts
    generate-config-matrix Generate unified entity/composite config comparison matrix
    generate-unified-map   Generate unified Bronze→Silver→Gold schema map CSV
    generate-field-diagnostics Generate field-level schema diagnostics CSV
    generate-field-spec    Generate deterministic field transformation spec CSV
    validate-configs       Validate unified pipeline YAML configs
    validate-unified-configs Validate legacy unified entity config structure
    analyze-gaps           Config gap analysis
"""

from __future__ import annotations

from scripts.engineering.common.cli_dispatch import dispatch_cli, module_command

COMMANDS: dict[str, str] = {
    "check-invariants": "scripts.schema.check_config_invariants",
    "check-required-fields": "scripts.schema.check_required_filter_fields",
    "audit-optionality": "scripts.schema.audit_effective_optionality",
    "check-config-paths": "scripts.schema.lint_config_paths",
    "generate-pipeline": "scripts.schema.generate_pipeline_schema",
    "generate-artifacts": "scripts.schema.generate_schema_artifacts",
    "generate-pubtype": "scripts.schema.generate_publication_type_classification_artifacts",
    "generate-contracts": "scripts.schema.generate_contracts",
    "generate-config-matrix": "scripts.schema.generate_config_matrix",
    "generate-unified-map": "scripts.schema.generate_unified_schema_map",
    "generate-field-diagnostics": "scripts.schema.generate_field_level_diagnostics",
    "generate-field-spec": "scripts.schema.generate_field_transformation_spec",
    "validate-configs": "scripts.schema.validate_pipeline_configs",
    "validate-unified-configs": "scripts.schema.validate_unified_configs",
    "analyze-gaps": "scripts.schema.config_gap_analysis",
}
COMMAND_SPECS = {name: module_command(module) for name, module in COMMANDS.items()}


def main(argv: list[str] | None = None) -> int:
    return dispatch_cli(
        argv,
        help_text=__doc__ or "",
        commands=COMMAND_SPECS,
    )


if __name__ == "__main__":
    raise SystemExit(main())
