#!/usr/bin/env python3
"""Analyze duplication in pipeline configs vs _base.yaml.

Usage: python scripts/analyze_config_duplication.py
Output: Report of duplicated keys and values per entity config.
"""

from collections import defaultdict
from pathlib import Path

import yaml


def load_yaml(path: Path) -> dict:
    """Load YAML file safely."""
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def flatten_dict(d: dict, parent_key: str = "", sep: str = ".") -> dict:
    """Flatten nested dict to dot-notation keys."""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict) and v:  # Non-empty dict
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def compare_configs(base: dict, entity: dict) -> dict:
    """Compare entity config against base, return duplicates."""
    base_flat = flatten_dict(base)
    entity_flat = flatten_dict(entity)

    duplicates = {}
    for key, value in entity_flat.items():
        if key in base_flat and base_flat[key] == value:
            duplicates[key] = value

    return duplicates


# Entity-specific keys that should NEVER be removed
ENTITY_SPECIFIC_KEYS = {
    "pipeline_name", "provider", "entity_type", "version", "description",
    "primary_keys", "silver_table", "gold_table", "gold_filters",
    "input_filter", "source_file", "dq_config_file", "dq_rules",
    "sort_by", "composite", "batch_size", "checkpoint_interval",
    # Paths are entity-specific
    "sink.bronze.path", "sink.silver.path", "sink.gold.path",
    "sink.silver.primary_key", "sink.silver.partition_by",
    "sink.silver.csv_export.path", "sink.gold.csv_export.path",
}

# Keys that could be defaults if repeated everywhere
POTENTIAL_DEFAULTS = {
    "sink.bronze.format",
    "sink.bronze.save_json",
    "sink.bronze.deterministic",
    "sink.bronze.save_metadata",
    "sink.silver.format",
    "sink.silver.mode",
    "sink.silver.on_schema_mismatch",
    "sink.silver.deterministic",
    "sink.silver.forensic_retention",
    "sink.silver.save_metadata",
    "sink.silver.classification",
    "sink.gold.enabled",
    "sink.gold.format",
    "sink.gold.mode",
    "sink.gold.deterministic",
    "sink.gold.save_metadata",
    "sink.gold.validation.strict",
    "dq_rules.soft_fail_threshold",
    "dq_rules.hard_fail_threshold",
    "dq_rules.strict_validation",
    "dq_rules.invalid_record_policy",
    "circuit_breaker.failure_threshold",
    "circuit_breaker.recovery_timeout",
    "source.type",
    "source.load_strategy",
}


def main():
    configs_root = Path("configs/pipelines")
    base_path = configs_root / "_base.yaml"

    base_config = load_yaml(base_path)
    if not base_config:
        print("ERROR: _base.yaml not found or empty")
        return

    print("=" * 80)
    print("CONFIG DUPLICATION ANALYSIS")
    print("=" * 80)

    total_duplicates = 0
    total_removable = 0
    report = defaultdict(list)

    # Track value occurrences across all configs
    value_counts = defaultdict(lambda: defaultdict(int))

    all_configs = []
    for provider_dir in sorted(configs_root.iterdir()):
        if not provider_dir.is_dir() or provider_dir.name.startswith(("_", ".")):
            continue

        for config_file in sorted(provider_dir.glob("*.yaml")):
            all_configs.append(config_file)
            entity_config = load_yaml(config_file)
            entity_flat = flatten_dict(entity_config)

            # Track values
            for key, value in entity_flat.items():
                value_counts[key][str(value)] += 1

    print(f"\nAnalyzing {len(all_configs)} entity configs...\n")

    # Find values that appear in ALL configs with same value
    print("=" * 80)
    print("KEYS WITH SAME VALUE IN ALL CONFIGS (potential defaults)")
    print("=" * 80)

    for key in sorted(value_counts.keys()):
        values = value_counts[key]
        if len(values) == 1:  # Same value everywhere
            value, count = list(values.items())[0]
            if count >= len(all_configs) * 0.8:  # In 80%+ of configs
                print(f"  {key}: {value[:60]}... ({count}/{len(all_configs)} configs)")

    print("\n" + "=" * 80)
    print("ANALYSIS PER CONFIG FILE")
    print("=" * 80)

    for config_file in all_configs:
        entity_config = load_yaml(config_file)
        duplicates = compare_configs(base_config, entity_config)

        # Filter to only show non-entity-specific duplicates
        removable = {}
        for key, value in duplicates.items():
            # Check if key starts with any entity-specific prefix
            is_entity_specific = False
            for es_key in ENTITY_SPECIFIC_KEYS:
                if key.startswith(es_key):
                    is_entity_specific = True
                    break

            if not is_entity_specific:
                removable[key] = value

        if removable:
            rel_path = config_file.relative_to(configs_root)
            print(f"\n{rel_path}:")
            for key, value in sorted(removable.items()):
                value_str = str(value)[:50] + "..." if len(str(value)) > 50 else str(value)
                total_removable += 1
                print(f"  [DUPLICATE] {key}: {value_str}")
            report[str(rel_path)] = removable

        total_duplicates += len(duplicates)

    # Check for patterns not in _base.yaml but repeated
    print("\n" + "=" * 80)
    print("PATTERNS REPEATED ACROSS CONFIGS (not in _base.yaml)")
    print("=" * 80)

    base_flat = flatten_dict(base_config)
    repeated_not_in_base = {}

    for key in sorted(value_counts.keys()):
        if key not in base_flat:
            values = value_counts[key]
            for value, count in values.items():
                if count >= len(all_configs) * 0.5:  # In 50%+ of configs
                    if key not in repeated_not_in_base:
                        repeated_not_in_base[key] = []
                    repeated_not_in_base[key].append((value, count))

    for key, occurrences in sorted(repeated_not_in_base.items()):
        # Skip entity-specific keys
        is_entity_specific = any(key.startswith(es) for es in ENTITY_SPECIFIC_KEYS)
        if not is_entity_specific:
            for value, count in occurrences:
                print(f"  {key}: {value[:60]}... ({count}/{len(all_configs)} configs)")

    print(f"\n{'=' * 80}")
    print(f"SUMMARY")
    print(f"{'=' * 80}")
    print(f"Total configs analyzed: {len(all_configs)}")
    print(f"Configs with removable duplicates: {len(report)}")
    print(f"Total removable duplicate fields: {total_removable}")

    # Recommendations
    print(f"\n{'=' * 80}")
    print("RECOMMENDATIONS")
    print("=" * 80)
    print("""
1. Add to _base.yaml (not currently defaults):
   - sink.silver.sort_by.ascending: true
   - sink.gold.sort_by.ascending: true
   - sink.silver.csv_export.enabled: true (+ defaults)
   - sink.gold.csv_export.enabled: true (+ defaults)

2. Remove from entity configs:
   - sort_by.ascending: true (when value matches default)
   - csv_export.path when it matches parent path
   - partition_by: [] (empty list - use null/omit instead)
   - Verbose dq_report sections when enabled: false

3. Consider:
   - Deriving csv_export.path from parent path automatically
   - Making batch_size=20 a default for chembl provider
""")


if __name__ == "__main__":
    main()
