#!/usr/bin/env python3
"""Inventory composition Protocol declarations and check the S3 shrink-only gate.

Usage::

    python -m scripts.engineering.qa report-composition-protocol-inventory --check
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Any

import yaml

from scripts.engineering.common.repo_paths import resolve_output_path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = (
    PROJECT_ROOT / "configs" / "quality" / "composition_protocol_inventory.yaml"
)


def _protocol_base_name(base: ast.expr) -> str | None:
    """Return the terminal name of a supported protocol base expression."""
    if isinstance(base, ast.Name):
        return base.id
    if isinstance(base, ast.Attribute):
        return base.attr
    return None


def _protocol_row(node: ast.AST, *, relative_path: str) -> dict[str, Any] | None:
    """Build an inventory row when ``node`` declares a Protocol class."""
    if not isinstance(node, ast.ClassDef):
        return None
    if "Protocol" not in (_protocol_base_name(base) for base in node.bases):
        return None
    return {
        "name": node.name,
        "path": relative_path,
        "line": node.lineno,
    }


def _protocol_rows(root: Path) -> list[dict[str, Any]]:
    """Collect Protocol declarations from a file or directory tree."""
    files = [root] if root.is_file() else sorted(root.rglob("*.py"))
    rows: list[dict[str, Any]] = []
    for py_file in files:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        rel = py_file.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
        for node in ast.walk(tree):
            row = _protocol_row(node, relative_path=rel)
            if row is not None:
                rows.append(row)
    return rows


def collect_scoped_protocols() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(_protocol_rows(PROJECT_ROOT / "src" / "bioetl" / "composition"))
    rows.extend(
        _protocol_rows(PROJECT_ROOT / "src" / "bioetl" / "application" / "ports")
    )
    domain_extra = (
        PROJECT_ROOT / "src" / "bioetl" / "domain" / "ports" / "entity_type.py",
        PROJECT_ROOT / "src" / "bioetl" / "domain" / "ports" / "pipeline_callbacks.py",
        PROJECT_ROOT / "src" / "bioetl" / "domain" / "ports" / "source_config.py",
        PROJECT_ROOT / "src" / "bioetl" / "domain" / "ports" / "config_mapper.py",
    )
    for path in domain_extra:
        if path.exists():
            rows.extend(_protocol_rows(path))
    return rows


def evaluate(config: dict[str, Any], live: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    expected_total = int(config["expected_total"])
    max_outside = int(config["max_composition_declarations_outside_contracts"])
    if len(live) != expected_total:
        errors.append(f"inventory live={len(live)} expected_total={expected_total}")
    outside = [
        row
        for row in live
        if str(row["path"]).startswith("src/bioetl/composition/")
        and "/contracts/" not in str(row["path"])
    ]
    if len(outside) > max_outside:
        errors.append(
            "composition Protocol declarations outside contracts "
            f"{len(outside)} exceed shrink-only max {max_outside}"
        )
    configured = config.get("protocols") or []
    if isinstance(configured, list) and len(configured) != expected_total:
        errors.append(
            f"yaml protocols={len(configured)} expected_total={expected_total}"
        )
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    config = yaml.safe_load(
        resolve_output_path(args.config).read_text(encoding="utf-8")
    )
    live = collect_scoped_protocols()
    errors = evaluate(config, live)
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(
        "composition protocol inventory ok: "
        f"total={len(live)} outside_contracts="
        f"{sum(1 for row in live if str(row['path']).startswith('src/bioetl/composition/') and '/contracts/' not in str(row['path']))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
