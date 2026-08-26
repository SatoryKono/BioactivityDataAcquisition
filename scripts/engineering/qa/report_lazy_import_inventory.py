#!/usr/bin/env python3
"""Count function-level lazy bioetl.* imports in composition (S4 / #9600)."""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path
from typing import Any

import yaml

from scripts.engineering.common.repo_paths import resolve_output_path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "quality" / "lazy_import_ratchet.yaml"
COMPOSITION = PROJECT_ROOT / "src" / "bioetl" / "composition"


def _imported_bioetl_modules(node: ast.AST) -> tuple[str, ...]:
    """Return BioETL modules imported by one AST node."""
    if isinstance(node, ast.ImportFrom):
        module = node.module or ""
        return (module,) if module.startswith("bioetl.") else ()
    if isinstance(node, ast.Import):
        return tuple(
            alias.name for alias in node.names if alias.name.startswith("bioetl.")
        )
    return ()


def _function_lazy_import_rows(
    fn: ast.FunctionDef | ast.AsyncFunctionDef,
    *,
    relative_path: str,
) -> list[dict[str, Any]]:
    """Build inventory rows for BioETL imports nested in one function."""
    return [
        {
            "path": relative_path,
            "function": fn.name,
            "line": getattr(node, "lineno", fn.lineno),
            "module": module,
        }
        for node in ast.walk(fn)
        for module in _imported_bioetl_modules(node)
    ]


def collect_lazy_imports(root: Path = COMPOSITION) -> list[dict[str, Any]]:
    """Collect function-level imports of BioETL modules below ``root``."""
    rows: list[dict[str, Any]] = []
    for py_file in sorted(root.rglob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        rel = py_file.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
        for fn in ast.walk(tree):
            if isinstance(fn, ast.FunctionDef | ast.AsyncFunctionDef):
                rows.extend(_function_lazy_import_rows(fn, relative_path=rel))
    return rows


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    args = parser.parse_args(argv)
    rows = collect_lazy_imports()
    config = yaml.safe_load(
        resolve_output_path(args.config).read_text(encoding="utf-8")
    )
    max_count = int(config["max_count"])
    if len(rows) > max_count:
        print(
            f"lazy bioetl imports {len(rows)} exceed shrink-only max_count={max_count}",
            file=sys.stderr,
        )
        return 1
    if len(rows) < max_count:
        print(
            f"shrink lazy_import_ratchet max_count from {max_count} to {len(rows)}",
            file=sys.stderr,
        )
        return 1
    print(f"lazy import ratchet ok: {len(rows)} == max_count {max_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
