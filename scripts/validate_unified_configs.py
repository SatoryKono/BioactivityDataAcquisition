#!/usr/bin/env python3
"""Validate unified config structure across all pipeline configs."""

import sys
from pathlib import Path

import yaml


REQUIRED_TOP_LEVEL = {
    "pipeline_name",
    "provider",
    "entity_type",
    "version",
    "description",
    "primary_keys",
    "silver_table",
    "gold_table",
    "sink",
    "input_filter",
    "gold_filters",
}

REQUIRED_SINK_LAYERS = {"bronze", "silver", "gold"}
REQUIRED_SINK_SILVER = {"path", "primary_key", "partition_by", "csv_export"}
REQUIRED_INPUT_FILTER = {"enabled"}
REQUIRED_GOLD_FILTERS = {"required_fields"}


def validate_config(path: Path) -> list[str]:
    """Validate config structure, return list of errors."""
    errors = []

    with open(path) as f:
        config = yaml.safe_load(f)

    if config is None:
        return [f"{path}: Empty config"]

    # Skip _defaults.yaml
    if path.name == "_defaults.yaml":
        return []

    rel_path = path.relative_to(Path("configs/pipelines"))

    # Check top-level keys
    missing_top = REQUIRED_TOP_LEVEL - set(config.keys())

    # source_file OR source is required
    if "source_file" not in config and "source" not in config:
        missing_top.add("source_file (or source)")
    missing_top.discard("source_file")  # Remove if checking both

    if missing_top:
        errors.append(f"{rel_path}: Missing required keys: {sorted(missing_top)}")

    # Check sink structure
    sink = config.get("sink", {})
    missing_sink = REQUIRED_SINK_LAYERS - set(sink.keys())
    if missing_sink:
        errors.append(f"{rel_path}: Missing sink layers: {sorted(missing_sink)}")

    # Check sink.silver
    silver = sink.get("silver", {})
    missing_silver = REQUIRED_SINK_SILVER - set(silver.keys())
    if missing_silver:
        errors.append(f"{rel_path}: Missing sink.silver keys: {sorted(missing_silver)}")

    # Check sink.gold
    gold = sink.get("gold", {})
    if "path" not in gold:
        errors.append(f"{rel_path}: Missing sink.gold.path")
    if "csv_export" not in gold:
        errors.append(f"{rel_path}: Missing sink.gold.csv_export")

    # Check input_filter
    input_filter = config.get("input_filter", {})
    if "enabled" not in input_filter:
        errors.append(f"{rel_path}: Missing input_filter.enabled")

    # Check gold_filters
    gold_filters = config.get("gold_filters", {})
    missing_gf = REQUIRED_GOLD_FILTERS - set(gold_filters.keys())
    if missing_gf:
        errors.append(f"{rel_path}: Missing gold_filters keys: {sorted(missing_gf)}")

    # Check for deprecated/redundant keys
    deprecated_keys = []
    if "transform" in config:
        deprecated_keys.append("transform (removed - not used by code)")

    # Check for redundant sink parameters that should use defaults
    redundant_sink = []
    if silver.get("format") == "delta":
        redundant_sink.append("sink.silver.format")
    if silver.get("mode") == "merge":
        redundant_sink.append("sink.silver.mode")
    if gold.get("format") == "delta":
        redundant_sink.append("sink.gold.format")
    if gold.get("mode") == "overwrite":
        redundant_sink.append("sink.gold.mode")

    # Only warn, don't error on redundant (they work, just unnecessary)
    if deprecated_keys:
        errors.append(f"{rel_path}: Deprecated keys: {deprecated_keys}")

    return errors


def main():
    configs_dir = Path("configs/pipelines")
    all_errors = []
    configs_validated = 0
    configs_with_errors = 0

    print("=" * 80)
    print("CONFIG VALIDATION REPORT")
    print("=" * 80)
    print()

    for yaml_file in sorted(configs_dir.rglob("*.yaml")):
        errors = validate_config(yaml_file)
        configs_validated += 1

        if errors:
            configs_with_errors += 1
            for e in errors:
                all_errors.append(e)
                print(f"  [ERROR] {e}")
        else:
            rel_path = yaml_file.relative_to(configs_dir)
            if yaml_file.name != "_defaults.yaml":
                print(f"  [OK] {rel_path}")

    print()
    print("=" * 80)
    print(f"Configs validated: {configs_validated}")
    print(f"Configs with errors: {configs_with_errors}")
    print(f"Total errors: {len(all_errors)}")
    print("=" * 80)

    if all_errors:
        print("\nValidation FAILED")
        return 1
    else:
        print("\nValidation PASSED: All configs have unified structure")
        return 0


if __name__ == "__main__":
    sys.exit(main())
