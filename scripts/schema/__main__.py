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

from pathlib import Path

from scripts.engineering.common.cli_dispatch import dispatch_cli, python_command

COMMANDS: dict[str, str] = {
    "check-invariants": "check_config_invariants.py",
    "check-required-fields": "check_required_filter_fields.py",
    "audit-optionality": "audit_effective_optionality.py",
    "check-config-paths": "lint_config_paths.py",
    "generate-pipeline": "generate_pipeline_schema.py",
    "generate-artifacts": "generate_schema_artifacts.py",
    "generate-pubtype": "generate_publication_type_classification_artifacts.py",
    "generate-contracts": "generate_contracts.py",
    "generate-config-matrix": "generate_config_matrix.py",
    "generate-unified-map": "generate_unified_schema_map.py",
    "generate-field-diagnostics": "generate_field_level_diagnostics.py",
    "generate-field-spec": "generate_field_transformation_spec.py",
    "validate-configs": "validate_pipeline_configs.py",
    "validate-unified-configs": "validate_unified_configs.py",
    "analyze-gaps": "config_gap_analysis.py",
}
COMMAND_SPECS = {name: python_command(script) for name, script in COMMANDS.items()}

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
