#!/usr/bin/env python3
"""Collect cross-owner private-module imports and check the shrink-only ratchet.

Usage::

    python -m scripts.engineering.qa report-private-import-inventory
    python -m scripts.engineering.qa report-private-import-inventory --check
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from scripts.engineering.common.repo_paths import resolve_output_path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SRC_DIR = PROJECT_ROOT / "src"
DEFAULT_CONFIG = PROJECT_ROOT / "configs" / "quality" / "private_import_ratchet.yaml"
DEFAULT_JSON_OUTPUT = (
    PROJECT_ROOT / "reports" / "quality" / "private-import-inventory.json"
)
SCHEMA_VERSION = 1
GENERATED_BY = "scripts.engineering.qa.report_private_import_inventory"


def _module_name_for_path(src_dir: Path, file_path: Path) -> str:
    rel_parts = file_path.relative_to(src_dir).with_suffix("").parts
    return ".".join(rel_parts)


def _collect_existing_modules(src_dir: Path) -> frozenset[str]:
    modules: set[str] = set()
    for py_file in src_dir.rglob("*.py"):
        rel_path = py_file.resolve().relative_to(src_dir.resolve())
        if py_file.name == "__init__.py":
            modules.add(".".join(rel_path.parent.parts))
            continue
        modules.add(".".join(rel_path.with_suffix("").parts))
    return frozenset(modules)


def _resolve_relative_module(
    *,
    importer_module: str,
    module: str | None,
    level: int,
) -> str | None:
    if level == 0:
        return module
    parent_parts = importer_module.split(".")[:-1]
    if level > len(parent_parts):
        return None
    base_parts = parent_parts[: len(parent_parts) - level + 1]
    if module:
        return ".".join([*base_parts, module])
    return ".".join(base_parts)


def _iter_candidate_import_targets(
    *,
    existing_modules: frozenset[str],
    importer_module: str,
    node: ast.AST,
) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names if alias.name.startswith("bioetl.")]
    if not isinstance(node, ast.ImportFrom):
        return []
    base_module = _resolve_relative_module(
        importer_module=importer_module,
        module=node.module,
        level=node.level,
    )
    if not base_module or not base_module.startswith("bioetl."):
        return []
    candidates = [base_module]
    for alias in node.names:
        if alias.name == "*":
            continue
        nested_module = f"{base_module}.{alias.name}"
        if nested_module in existing_modules:
            candidates.append(nested_module)
    return candidates


def _is_private_module(module: str) -> bool:
    return any(part.startswith("_") for part in module.split("."))


def _parse_source_file(
    py_file: Path,
    *,
    resolved_src: Path,
) -> tuple[str, ast.AST] | None:
    """Return a source-relative path and parsed tree for one readable source file."""
    try:
        rel_path = py_file.resolve().relative_to(resolved_src).as_posix()
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    except (OSError, SyntaxError, ValueError):
        return None
    return rel_path, tree


def _is_external_private_target(target_module: str, *, importer_owner: str) -> bool:
    """Return whether a target is private and owned by a different package."""
    return _is_private_module(target_module) and (
        target_module.rsplit(".", 1)[0] != importer_owner
    )


def _external_private_imports_in_tree(
    tree: ast.AST,
    *,
    existing_modules: frozenset[str],
    importer_module: str,
) -> list[tuple[str, int]]:
    """Collect external private targets and line numbers from one parsed tree."""
    importer_owner = importer_module.rsplit(".", 1)[0]
    return [
        (target_module, getattr(node, "lineno", 0))
        for node in ast.walk(tree)
        for target_module in _iter_candidate_import_targets(
            existing_modules=existing_modules,
            importer_module=importer_module,
            node=node,
        )
        if _is_external_private_target(
            target_module,
            importer_owner=importer_owner,
        )
    ]


def collect_external_private_imports(
    src_dir: Path = SRC_DIR,
) -> dict[tuple[str, str], list[int]]:
    """Return cross-owner private-module import pairs keyed by (rel_path, target)."""
    violations: dict[tuple[str, str], list[int]] = {}
    existing_modules = _collect_existing_modules(src_dir)
    resolved_src = src_dir.resolve()
    for py_file in sorted(src_dir.rglob("*.py")):
        parsed = _parse_source_file(py_file, resolved_src=resolved_src)
        if parsed is None:
            continue
        rel_path, tree = parsed
        importer_module = _module_name_for_path(src_dir, py_file)
        for target_module, line in _external_private_imports_in_tree(
            tree,
            existing_modules=existing_modules,
            importer_module=importer_module,
        ):
            key = (rel_path, target_module)
            violations.setdefault(key, []).append(line)
    return violations


def load_ratchet_config(path: Path = DEFAULT_CONFIG) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid ratchet config: {path}")
    return payload


def allowed_pairs_from_config(config: dict[str, Any]) -> frozenset[tuple[str, str]]:
    pairs = config.get("pairs")
    if not isinstance(pairs, list):
        raise ValueError("private_import_ratchet.yaml: pairs must be a list")
    allowed: set[tuple[str, str]] = set()
    for row in pairs:
        if not isinstance(row, dict):
            raise ValueError("private_import_ratchet.yaml: each pair must be a mapping")
        importer = row.get("importer")
        target = row.get("target")
        if not isinstance(importer, str) or not isinstance(target, str):
            raise ValueError(
                "private_import_ratchet.yaml: importer/target must be strings"
            )
        allowed.add((importer, target))
    return frozenset(allowed)


def build_payload(
    *,
    src_dir: Path = SRC_DIR,
    config_path: Path = DEFAULT_CONFIG,
) -> dict[str, Any]:
    config = load_ratchet_config(config_path)
    observed = collect_external_private_imports(src_dir)
    allowed = allowed_pairs_from_config(config)
    max_count = int(config["max_count"])
    observed_pairs = sorted(observed)
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_by": GENERATED_BY,
        "max_count": max_count,
        "allowlist_count": len(allowed),
        "observed_count": len(observed_pairs),
        "strict_mode": bool(config.get("strict_mode", False)),
        "observed": [
            {
                "importer": importer,
                "target": target,
                "lines": observed[(importer, target)],
            }
            for importer, target in observed_pairs
        ],
        "unexpected": [
            {"importer": importer, "target": target}
            for importer, target in sorted(set(observed) - allowed)
        ],
        "unused_allowlist": [
            {"importer": importer, "target": target}
            for importer, target in sorted(allowed - set(observed))
        ],
    }


def evaluate_ratchet(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    max_count = int(payload["max_count"])
    allowlist_count = int(payload["allowlist_count"])
    observed_count = int(payload["observed_count"])
    if allowlist_count != max_count:
        errors.append(
            f"allowlist_count={allowlist_count} must equal max_count={max_count}"
        )
    if observed_count > max_count:
        errors.append(
            f"observed_count={observed_count} exceeds shrink-only max_count={max_count}"
        )
    unexpected = payload.get("unexpected") or []
    if unexpected:
        rendered = ", ".join(
            f"{row['importer']} -> {row['target']}"
            for row in unexpected
            if isinstance(row, dict)
        )
        errors.append(f"new cross-owner private imports: {rendered}")
    unused = payload.get("unused_allowlist") or []
    if unused or observed_count < max_count:
        errors.append(
            "shrink max_count to the live observed_count "
            f"({observed_count}); remove unused allowlist pairs"
        )
    return errors


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUTPUT)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    payload = build_payload(config_path=resolve_output_path(args.config))
    json_text = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    json_out = resolve_output_path(args.json_out)
    errors = evaluate_ratchet(payload)
    if args.check:
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 1
        return 0
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json_text, encoding="utf-8")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
