#!/usr/bin/env python3
"""Generate comparison matrix for unified entity/composite configs."""

from __future__ import annotations

import argparse
import csv
import io
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


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="Fail if committed config matrix/report artifacts are stale.",
    )
    mode.add_argument(
        "--update",
        action="store_true",
        help="Write generated config matrix/report artifacts (default).",
    )
    parser.add_argument(
        "--matrix-output",
        type=Path,
        default=Path("docs/04-reference/config_comparison_matrix.csv"),
        help="CSV matrix output path.",
    )
    parser.add_argument(
        "--report-output",
        type=Path,
        default=Path("docs/config-discrepancies-report.md"),
        help="Markdown discrepancy report output path.",
    )
    return parser.parse_args(argv)


def _build_artifact_contents() -> tuple[str, str, int, int, int]:
    """Build matrix/report contents without writing files."""
    configs = _collect_configs()
    all_keys = sorted(
        {key for values in configs.values() for key in values}, key=_sort_key
    )
    config_names = sorted(configs.keys())

    if configs:
        common = set.intersection(*(set(values.keys()) for values in configs.values()))
    else:
        common = set()

    partial = [key for key in all_keys if key not in common]
    matrix_handle = io.StringIO(newline="")
    writer = csv.writer(matrix_handle)
    writer.writerow(["Parameter Path", *config_names])
    for key in all_keys:
        row = [key]
        for cfg_name in config_names:
            row.append(configs[cfg_name].get(key, "—"))
        writer.writerow(row)

    report_lines = [
        "# Config Discrepancies Report",
        "",
        f"Total configs: {len(configs)}",
        f"Total unique parameters: {len(all_keys)}",
        "",
        "## Inconsistent Parameters",
        "",
    ]
    for key in partial:
        present_in = [cfg for cfg, data in configs.items() if key in data]
        report_lines.append(
            f"- `{key}` ({len(present_in)}/{len(configs)}): {', '.join(present_in)}"
        )
    report_lines.append("")
    return (
        matrix_handle.getvalue(),
        "\n".join(report_lines),
        len(all_keys),
        len(configs),
        len(partial),
    )


def _write_artifacts(
    *,
    matrix_path: Path,
    report_path: Path,
    matrix_content: str,
    report_content: str,
) -> None:
    matrix_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    matrix_path.write_text(matrix_content, encoding="utf-8", newline="")
    report_path.write_text(report_content, encoding="utf-8", newline="")


def _artifact_matches(path: Path, expected: str) -> bool:
    if not path.exists():
        print(f"[drift] missing: {path}")
        return False
    with path.open(encoding="utf-8", newline="") as handle:
        actual = handle.read()
    if actual == expected:
        return True
    print(f"[drift] mismatch: {path}")
    return False


def main(argv: list[str] | None = None) -> int:
    """Generate or check CSV and Markdown comparison outputs."""
    args = _parse_args(argv)
    matrix_content, report_content, parameter_count, config_count, partial_count = (
        _build_artifact_contents()
    )
    if args.check:
        ok = _artifact_matches(
            args.matrix_output,
            matrix_content,
        ) and _artifact_matches(args.report_output, report_content)
        if ok:
            print("[ok] config matrix artifacts are up to date")
            return 0
        print("[hint] run: python -m scripts.schema generate-config-matrix --update")
        return 1

    _write_artifacts(
        matrix_path=args.matrix_output,
        report_path=args.report_output,
        matrix_content=matrix_content,
        report_content=report_content,
    )
    print(f"Matrix saved to {args.matrix_output}")
    print(f"Total parameters: {parameter_count}")
    print(f"Total configs: {config_count}")
    print("\n" + "=" * 80)
    print("PARAMETER PRESENCE SUMMARY")
    print("=" * 80)
    print(f"Inconsistent parameters: {partial_count}")
    print(f"Discrepancy report saved to {args.report_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
