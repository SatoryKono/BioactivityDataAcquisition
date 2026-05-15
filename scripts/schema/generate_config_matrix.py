#!/usr/bin/env python3
"""Generate comparison matrix for unified entity/composite configs."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import yaml


def flatten_dict(d: dict[str, Any], parent_key: str = "") -> dict[str, Any]:
    """Flatten nested dict to dot-notation keys."""
    items: dict[str, Any] = {}
    for key, value in d.items():
        new_key = f"{parent_key}.{key}" if parent_key else key
        if isinstance(value, dict):
            items[new_key] = "(dict)"
            items.update(flatten_dict(value, new_key))
        elif isinstance(value, list):
            items[new_key] = json.dumps(value, ensure_ascii=False) if value else "[]"
        else:
            items[new_key] = str(value) if value is not None else "null"
    return items


def load_config(path: Path) -> dict[str, Any]:
    """Load a YAML config file as a mapping."""
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def _collect_configs() -> dict[str, dict[str, Any]]:
    configs: dict[str, dict[str, Any]] = {}

    entities_dir = Path("configs/entities")
    for yaml_file in sorted(entities_dir.rglob("*.yaml")):
        if yaml_file.name.startswith("_"):
            continue
        rel = yaml_file.relative_to(entities_dir)
        name = f"entity/{rel.parent.name}/{rel.stem}"
        configs[name] = flatten_dict(load_config(yaml_file))

    composites_dir = Path("configs/composites")
    for yaml_file in sorted(composites_dir.glob("*.yaml")):
        if yaml_file.name.startswith("_"):
            continue
        name = f"composite/{yaml_file.stem}"
        configs[name] = flatten_dict(load_config(yaml_file))

    return configs


def _sort_key(path: str) -> tuple[int, list[str]]:
    parts = path.split(".")
    return (len(parts), parts)


def main() -> None:
    """Generate CSV and Markdown comparison outputs."""
    configs = _collect_configs()
    all_keys = sorted(
        {key for values in configs.values() for key in values}, key=_sort_key
    )
    config_names = sorted(configs.keys())

    output_path = Path("docs/04-reference/config_comparison_matrix.csv")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Parameter Path", *config_names])
        for key in all_keys:
            row = [key]
            for cfg_name in config_names:
                row.append(configs[cfg_name].get(key, "—"))
            writer.writerow(row)

    print(f"Matrix saved to {output_path}")
    print(f"Total parameters: {len(all_keys)}")
    print(f"Total configs: {len(configs)}")

    print("\n" + "=" * 80)
    print("PARAMETER PRESENCE SUMMARY")
    print("=" * 80)
    if configs:
        common = set.intersection(*(set(values.keys()) for values in configs.values()))
        print(f"Common parameters in all configs: {len(common)}")
    else:
        common = set()
        print("No configs discovered.")

    partial = [key for key in all_keys if key not in common]
    print(f"Inconsistent parameters: {len(partial)}")

    report_path = Path("docs/config-discrepancies-report.md")
    with report_path.open("w", encoding="utf-8") as handle:
        handle.write("# Config Discrepancies Report\n\n")
        handle.write(f"Total configs: {len(configs)}\n")
        handle.write(f"Total unique parameters: {len(all_keys)}\n\n")
        handle.write("## Inconsistent Parameters\n\n")
        for key in partial:
            present_in = [cfg for cfg, data in configs.items() if key in data]
            handle.write(
                f"- `{key}` ({len(present_in)}/{len(configs)}): {', '.join(present_in)}\n"
            )

    print(f"Discrepancy report saved to {report_path}")


if __name__ == "__main__":
    main()
