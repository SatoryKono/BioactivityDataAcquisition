#!/usr/bin/env python3
"""Validate pipeline YAML configs against JSON Schema.

Usage:
    python scripts/validate_pipeline_configs.py [--verbose]

Exit codes:
    0 - All configs valid
    1 - Validation errors found
    2 - Schema file not found
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

try:
    import jsonschema
except ImportError:
    sys.stderr.write("ERROR: jsonschema not installed. Run: pip install jsonschema\n")
    sys.exit(2)


def load_schema(schema_path: Path) -> dict[str, Any]:
    """Load JSON Schema from file."""
    if not schema_path.exists():
        sys.stderr.write(f"ERROR: Schema file not found: {schema_path}\n")
        sys.exit(2)
    raw_schema: dict[str, Any] = json.loads(schema_path.read_text())
    return raw_schema


def find_config_files(configs_dir: Path) -> list[Path]:
    """Find all entity config files (excluding base configs)."""
    return [
        p
        for p in configs_dir.rglob("*.yaml")
        if not p.name.startswith("_") and p.parent.name != "_providers"
    ]


def validate_config(config_path: Path, schema: dict[str, Any]) -> tuple[bool, str]:
    """Validate single config file against schema."""
    try:
        config = yaml.safe_load(config_path.read_text())
        jsonschema.validate(config, schema)
        return True, ""
    except yaml.YAMLError as e:
        return False, f"YAML parse error: {e}"
    except jsonschema.ValidationError as e:
        return False, f"Schema validation: {e.message} at {'.'.join(map(str, e.path))}"


def validate_paths_hierarchy(config: dict[str, Any]) -> list[str]:
    """Check that paths follow {provider}/{entity} hierarchy."""
    warnings = []
    provider = config.get("provider", "")
    entity = config.get("entity_type", "")

    for layer in ["bronze", "silver", "gold"]:
        sink = config.get("sink", {}).get(layer, {})
        path = sink.get("path", "")
        expected_suffix = f"{provider}/{entity}"

        if path and not path.endswith(expected_suffix):
            warnings.append(
                f"sink.{layer}.path should end with '{expected_suffix}', got: {path}"
            )

    return warnings


def validate_sort_by_present(config: dict[str, Any]) -> list[str]:
    """Check that sort_by is defined for determinism (ADR-014)."""
    warnings = []

    for layer in ["silver", "gold"]:
        sink = config.get("sink", {}).get(layer, {})
        if "sort_by" not in sink:
            warnings.append(f"sink.{layer}.sort_by missing (ADR-014 determinism)")

    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate pipeline configs")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as errors (path hierarchy, sort_by)",
    )
    args = parser.parse_args()

    configs_dir = Path("configs/pipelines")
    schema_dir = Path("configs/_schema")
    schema_path = schema_dir / "pipeline.json"
    composite_schema_path = schema_dir / "composite.json"

    schema = load_schema(schema_path)
    composite_schema = load_schema(composite_schema_path)
    config_files = find_config_files(configs_dir)

    errors = []
    warnings = []

    for config_path in config_files:
        if args.verbose:
            sys.stdout.write(f"Checking: {config_path}\n")

        is_composite_config = "composite" in config_path.parts
        active_schema = composite_schema if is_composite_config else schema

        # Schema validation
        valid, error_msg = validate_config(config_path, active_schema)
        if not valid:
            errors.append(f"{config_path}: {error_msg}")
            continue

        # Load config for additional checks
        config = yaml.safe_load(config_path.read_text())

        # Hierarchy and sort checks apply only to standard pipeline configs.
        if is_composite_config:
            continue

        # Path hierarchy check
        path_warnings = validate_paths_hierarchy(config)
        for w in path_warnings:
            warnings.append(f"{config_path}: {w}")

        # sort_by check
        sort_warnings = validate_sort_by_present(config)
        for w in sort_warnings:
            warnings.append(f"{config_path}: {w}")

    # Output results
    if errors:
        sys.stderr.write("\n❌ ERRORS:\n")
        for e in errors:
            sys.stderr.write(f"  {e}\n")

    if warnings:
        sys.stdout.write("\n⚠️  WARNINGS:\n")
        for w in warnings:
            sys.stdout.write(f"  {w}\n")

    if not errors and not warnings:
        sys.stdout.write(f"✅ All {len(config_files)} configs valid\n")
        return 0

    if errors:
        return 1

    if args.strict and warnings:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
