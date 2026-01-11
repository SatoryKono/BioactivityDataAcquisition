#!/usr/bin/env python3
"""
Generate comparison matrix for pipeline configs.

This script analyzes all pipeline config files and produces:
1. A CSV matrix showing which parameters exist in which configs
2. A summary of discrepancies categorized by type
"""

import csv
import json
from pathlib import Path
from typing import Any

import yaml


def flatten_dict(d: dict, parent_key: str = "") -> dict[str, Any]:
    """Flatten nested dict to dot-notation keys."""
    items = {}
    for k, v in d.items():
        new_key = f"{parent_key}.{k}" if parent_key else k
        if isinstance(v, dict):
            items[new_key] = "(dict)"
            items.update(flatten_dict(v, new_key))
        elif isinstance(v, list):
            items[new_key] = json.dumps(v) if v else "[]"
        else:
            items[new_key] = str(v) if v is not None else "null"
    return items


def load_config(path: Path) -> dict:
    """Load YAML config file."""
    with open(path) as f:
        return yaml.safe_load(f) or {}


def get_config_name(yaml_file: Path, configs_dir: Path) -> str:
    """Generate readable config name from path."""
    rel_path = yaml_file.relative_to(configs_dir)
    parts = list(rel_path.parts)
    # Remove .yaml extension
    parts[-1] = parts[-1].replace(".yaml", "")
    return "/".join(parts)


def main():
    configs_dir = Path("configs/pipelines")

    # Collect all configs
    configs: dict[str, dict[str, Any]] = {}
    all_keys: set[str] = set()

    for yaml_file in sorted(configs_dir.rglob("*.yaml")):
        config_name = get_config_name(yaml_file, configs_dir)

        data = load_config(yaml_file)
        flat = flatten_dict(data)
        configs[config_name] = flat
        all_keys.update(flat.keys())

    # Sort keys hierarchically
    def sort_key(x: str) -> tuple:
        parts = x.split(".")
        return (len(parts), parts)

    sorted_keys = sorted(all_keys, key=sort_key)

    # Write CSV matrix
    output_path = Path("docs/config_comparison_matrix.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        # Header
        config_names = sorted(configs.keys())
        writer.writerow(["Parameter Path", *config_names])

        # Data rows
        for key in sorted_keys:
            row = [key]
            for cfg_name in config_names:
                value = configs[cfg_name].get(key)
                if value is None:
                    row.append("—")
                else:
                    row.append(value)
            writer.writerow(row)

    print(f"Matrix saved to {output_path}")
    print(f"Total parameters: {len(sorted_keys)}")
    print(f"Total configs: {len(configs)}")

    # Generate summary statistics
    print("\n" + "=" * 80)
    print("PARAMETER PRESENCE SUMMARY")
    print("=" * 80)

    # Categorize parameters
    defaults_keys = set(configs.get("_defaults", {}).keys())
    entity_configs = {k: v for k, v in configs.items() if k != "_defaults"}

    # Parameters only in defaults
    only_defaults = defaults_keys - set().union(
        *[set(v.keys()) for v in entity_configs.values()]
    )

    # Parameters in ALL entity configs
    if entity_configs:
        common_entity = set.intersection(
            *[set(v.keys()) for v in entity_configs.values()]
        )
    else:
        common_entity = set()

    # Parameters only in SOME entity configs
    any_entity = set().union(*[set(v.keys()) for v in entity_configs.values()])
    partial_entity = any_entity - common_entity

    # Parameters missing in defaults but present in entities
    missing_defaults = any_entity - defaults_keys

    print("\n1. Parameters ONLY in _defaults (not used in entity configs):")
    for k in sorted(only_defaults):
        print(f"   - {k}")

    print(f"\n2. Parameters in ALL entity configs ({len(common_entity)}):")
    for k in sorted(common_entity):
        print(f"   - {k}")

    print("\n3. Parameters in SOME entity configs (inconsistent):")
    partial_by_key = {}
    for k in sorted(partial_entity):
        present_in = [cfg for cfg, data in entity_configs.items() if k in data]
        partial_by_key[k] = present_in
        count = len(present_in)
        print(f"   - {k} ({count}/{len(entity_configs)} configs)")

    print("\n4. Parameters MISSING in _defaults (candidates for addition):")
    for k in sorted(
        missing_defaults - set(flatten_dict({"sink": {}, "input_filter": {}}).keys())
    ):
        if not any(skip in k for skip in ["sink.", "input_filter.", "gold_filters."]):
            print(f"   - {k}")

    # Write detailed report
    report_path = Path("docs/config_discrepancies_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Config Discrepancies Report\n\n")
        f.write(f"Generated: {__import__('datetime').datetime.now().isoformat()}\n\n")
        f.write(f"Total configs: {len(configs)}\n")
        f.write(f"Total unique parameters: {len(sorted_keys)}\n\n")

        f.write("## 1. Parameters by Category\n\n")

        # Group parameters by top-level key
        by_category = {}
        for key in sorted_keys:
            category = key.split(".")[0]
            by_category.setdefault(category, []).append(key)

        for category, keys in sorted(by_category.items()):
            f.write(f"### {category}\n\n")
            f.write("| Parameter | Presence |\n")
            f.write("|-----------|----------|\n")
            for key in keys:
                present_count = sum(1 for cfg in configs.values() if key in cfg)
                f.write(f"| `{key}` | {present_count}/{len(configs)} |\n")
            f.write("\n")

        f.write("## 2. Entity Config Comparison\n\n")

        # Key structural parameters
        structural_keys = [
            "pipeline_name",
            "provider",
            "entity_type",
            "version",
            "description",
            "primary_keys",
            "silver_table",
            "gold_table",
            "source_file",
            "source",
            "transform",
            "dq_rules",
            "circuit_breaker",
            "rate_limit",
            "gold_filters",
            "sink",
            "input_filter",
        ]

        f.write("| Config | " + " | ".join(structural_keys) + " |\n")
        f.write("|" + "--------|" * (len(structural_keys) + 1) + "\n")

        for cfg_name in sorted(entity_configs.keys()):
            cfg_data = entity_configs[cfg_name]
            row = [cfg_name]
            for key in structural_keys:
                if key in cfg_data or any(k.startswith(f"{key}.") for k in cfg_data):
                    row.append("✓")
                else:
                    row.append("—")
            f.write("| " + " | ".join(row) + " |\n")

        f.write("\n## 3. Discrepancy Categories\n\n")

        f.write("### A. Missing in _defaults (should be added)\n\n")
        for k in sorted(missing_defaults):
            if not any(
                skip in k for skip in ["sink.", "gold_filters.", "input_filter."]
            ):
                present_in = [cfg for cfg, data in entity_configs.items() if k in data]
                f.write(f"- `{k}` - present in: {', '.join(present_in)}\n")

        f.write("\n### B. Inconsistent presence across entity configs\n\n")
        for k, present_in in sorted(partial_by_key.items()):
            if len(present_in) > 1 and len(present_in) < len(entity_configs):
                f.write(f"- `{k}`\n")
                f.write(
                    f"  - Present in ({len(present_in)}): {', '.join(present_in)}\n"
                )
                missing = set(entity_configs.keys()) - set(present_in)
                f.write(f"  - Missing in ({len(missing)}): {', '.join(missing)}\n")

        f.write("\n### C. Structural inconsistencies\n\n")

        # Check for source vs source_file
        source_configs = [
            cfg for cfg, data in entity_configs.items() if "source" in data
        ]
        source_file_configs = [
            cfg for cfg, data in entity_configs.items() if "source_file" in data
        ]

        f.write("#### source vs source_file\n\n")
        f.write(f"- Using `source`: {', '.join(source_configs) or 'none'}\n")
        f.write(
            f"- Using `source_file`: {', '.join(source_file_configs) or 'none'}\n\n"
        )

        # Check for transform presence
        transform_configs = [
            cfg
            for cfg, data in entity_configs.items()
            if "transform" in data or any(k.startswith("transform.") for k in data)
        ]
        f.write("#### transform block\n\n")
        f.write(f"- Has `transform`: {', '.join(transform_configs) or 'none'}\n")
        f.write(
            f"- No `transform`: {', '.join(set(entity_configs.keys()) - set(transform_configs))}\n\n"
        )

        # Check for gold_table presence
        gold_table_configs = [
            cfg for cfg, data in entity_configs.items() if "gold_table" in data
        ]
        f.write("#### gold_table presence\n\n")
        f.write(f"- Has `gold_table`: {', '.join(gold_table_configs) or 'none'}\n")
        f.write(
            f"- Missing `gold_table`: {', '.join(set(entity_configs.keys()) - set(gold_table_configs))}\n"
        )

    print(f"\nDetailed report saved to {report_path}")


if __name__ == "__main__":
    main()
