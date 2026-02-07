#!/usr/bin/env python3
"""CI check for root schema inventory, generators, and orphan detection.

Checks model-like schema definitions in configured roots and validates that each
schema has at least one usage in runtime code or tests.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG = Path("configs/schema_roots.yaml")

MODEL_TYPES = ("BaseModel", "dataclass", "TypedDict", "Protocol", "Pandera")


@dataclass(frozen=True)
class SchemaSymbol:
    name: str
    model_type: str
    file: Path
    line: int


def _is_name(node: ast.expr, *targets: str) -> bool:
    if isinstance(node, ast.Name):
        return node.id in targets
    if isinstance(node, ast.Attribute):
        return node.attr in targets
    return False


def classify_class(node: ast.ClassDef) -> set[str]:
    types: set[str] = set()

    if any(_is_name(base, "BaseModel") for base in node.bases):
        types.add("BaseModel")
    if any(_is_name(base, "TypedDict") for base in node.bases):
        types.add("TypedDict")
    if any(_is_name(base, "Protocol") for base in node.bases):
        types.add("Protocol")
    if any(_is_name(base, "DataFrameModel") for base in node.bases):
        types.add("Pandera")

    for deco in node.decorator_list:
        if isinstance(deco, ast.Call):
            if _is_name(deco.func, "dataclass"):
                types.add("dataclass")
        elif _is_name(deco, "dataclass"):
            types.add("dataclass")

    return types


def load_config(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def iter_python_files(globs: list[str]) -> list[Path]:
    files: set[Path] = set()
    for pattern in globs:
        files.update(Path().glob(pattern))
    return sorted(f for f in files if f.is_file() and f.suffix == ".py")


def collect_symbols(files: list[Path]) -> list[SchemaSymbol]:
    result: list[SchemaSymbol] = []
    for file in files:
        tree = ast.parse(file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for model_type in classify_class(node):
                    result.append(
                        SchemaSymbol(
                            name=node.name,
                            model_type=model_type,
                            file=file,
                            line=node.lineno,
                        )
                    )
    return result


def collect_usages(symbols: list[SchemaSymbol], usage_globs: list[str]) -> dict[str, set[Path]]:
    all_files = iter_python_files(usage_globs)
    by_name: dict[str, set[Path]] = defaultdict(set)

    symbol_names = {symbol.name for symbol in symbols}
    defining_files: dict[str, set[Path]] = defaultdict(set)
    for symbol in symbols:
        defining_files[symbol.name].add(symbol.file)

    for file in all_files:
        identifiers = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", file.read_text(encoding="utf-8")))
        for name in identifiers.intersection(symbol_names):
            if file not in defining_files[name]:
                by_name[name].add(file)

    return by_name


def build_medallion_generation_block(config_glob: str, generators: dict[str, Any]) -> list[dict[str, str]]:
    block: list[dict[str, str]] = []
    for cfg in sorted(Path().glob(config_glob)):
        if cfg.name.startswith("_"):
            continue
        rel = cfg.as_posix()
        parts = cfg.parts
        try:
            i = parts.index("pipelines")
            provider, entity = parts[i + 1], cfg.stem
        except (ValueError, IndexError):
            continue

        block.append(
            {
                "pipeline": f"{provider}_{entity}",
                "config": rel,
                "bronze_generator": generators["bronze_template"].format(
                    provider=provider, entity=entity
                ),
                "silver_generator": generators["silver_template"].format(
                    provider=provider, entity=entity
                ),
                "gold_generator": generators["gold_template"].format(
                    provider=provider, entity=entity
                ),
            }
        )
    return block


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--report-json", type=Path)
    parser.add_argument("--fail-on-orphans", action="store_true")
    args = parser.parse_args()

    cfg = load_config(args.config)
    schema_files = iter_python_files(cfg["root_schema_globs"])
    symbols = collect_symbols(schema_files)
    usages = collect_usages(symbols, cfg["usage_globs"])

    inventory: dict[str, list[dict[str, Any]]] = {k: [] for k in MODEL_TYPES}
    for symbol in symbols:
        inventory[symbol.model_type].append(
            {
                "name": symbol.name,
                "file": symbol.file.as_posix(),
                "line": symbol.line,
                "usages": sorted(path.as_posix() for path in usages.get(symbol.name, set())),
            }
        )

    orphans = [
        item
        for t in MODEL_TYPES
        for item in inventory[t]
        if not item["usages"]
    ]

    medallion_block = build_medallion_generation_block(
        cfg["pipeline_config_glob"], cfg["medallion_generators"]
    )

    report = {
        "root_schema_globs": cfg["root_schema_globs"],
        "inventory": inventory,
        "summary": {k: len(v) for k, v in inventory.items()},
        "orphans": orphans,
        "medallion_schema_generation": medallion_block,
    }

    print("Schema inventory summary:")
    for k in MODEL_TYPES:
        print(f"  - {k}: {report['summary'][k]}")
    print(f"  - Orphans: {len(orphans)} (usage includes tests/**)")
    print(
        "  - Medallion generation entries: "
        f"{len(report['medallion_schema_generation'])} from {cfg['pipeline_config_glob']}"
    )

    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"Report written to: {args.report_json}")

    if orphans:
        print("\nOrphan schemas:")
        for orphan in orphans:
            print(f"  - {orphan['name']} ({orphan['file']}:{orphan['line']})")
        if args.fail_on_orphans:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
