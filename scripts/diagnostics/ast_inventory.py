#!/usr/bin/env python3
"""AST-based inventory of all Python files in the bioetl package.

Parses every .py file, collects classes, functions, constants, and type aliases,
groups by architectural layer, and outputs summary statistics plus a detailed
JSON inventory.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SRC_ROOT = Path("/home/user/BioactivityDataAcquisition/src/bioetl")
OUTPUT_JSON = Path(
    "/home/user/BioactivityDataAcquisition/reports/inventory/inventory.json"
)

LAYERS = ("domain", "application", "infrastructure", "composition", "interfaces")

# NAME-001 allowed suffixes for classes
NAME001_SUFFIXES = (
    "Factory",
    "Client",
    "Port",
    "Service",
    "Transformer",
    "Error",
    "Schema",
    "Config",
    "Adapter",
    "Model",
)

UPPER_SNAKE_RE = re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _layer_for(path: Path) -> str:
    """Determine the architectural layer from a file path."""
    rel = path.relative_to(SRC_ROOT)
    parts = rel.parts
    if len(parts) >= 1 and parts[0] in LAYERS:
        return parts[0]
    return "root"


def _loc(node: ast.AST) -> int:
    """Lines of code for a node (end_lineno - lineno + 1)."""
    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", None)
    if start is not None and end is not None:
        return end - start + 1
    return 0


def _is_public(name: str) -> bool:
    return not name.startswith("_")


def _method_info(node):
    return {
        "name": node.name,
        "is_async": isinstance(node, ast.AsyncFunctionDef),
        "is_public": _is_public(node.name),
        "loc": _loc(node),
        "lineno": node.lineno,
    }


def _has_name001_suffix(name: str) -> bool:
    """Check whether a class name ends with one of the NAME-001 suffixes."""
    return any(name.endswith(suffix) for suffix in NAME001_SUFFIXES)


# ---------------------------------------------------------------------------
# Core collection
# ---------------------------------------------------------------------------


def collect_from_file(filepath: Path) -> dict[str, Any]:
    """Parse a single .py file and return its inventory."""
    source = filepath.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError as exc:
        return {
            "file": str(filepath),
            "error": f"SyntaxError: {exc}",
            "classes": [],
            "functions": [],
            "constants": [],
            "type_aliases": [],
        }

    classes = []
    functions = []
    constants = []
    type_aliases = []

    for node in ast.iter_child_nodes(tree):
        # --- Classes -------------------------------------------------------
        if isinstance(node, ast.ClassDef):
            bases = []
            for base in node.bases:
                if isinstance(base, ast.Name):
                    bases.append(base.id)
                elif isinstance(base, ast.Attribute):
                    bases.append(ast.unparse(base))
                else:
                    bases.append(ast.unparse(base))

            methods_public = []
            methods_private = []
            for item in ast.iter_child_nodes(node):
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    info = _method_info(item)
                    if info["is_public"]:
                        methods_public.append(info)
                    else:
                        methods_private.append(info)

            cls_info = {
                "name": node.name,
                "bases": bases,
                "public_methods": methods_public,
                "private_methods": methods_private,
                "loc": _loc(node),
                "lineno": node.lineno,
                "has_name001_suffix": _has_name001_suffix(node.name),
            }
            classes.append(cls_info)

        # --- Functions / AsyncFunctions ------------------------------------
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_info = {
                "name": node.name,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "is_public": _is_public(node.name),
                "loc": _loc(node),
                "lineno": node.lineno,
            }
            functions.append(func_info)

        # --- Type aliases (annotated assignment with TypeAlias) ------------
        elif isinstance(node, ast.AnnAssign):
            target = node.target
            annotation = node.annotation
            is_type_alias = False
            if isinstance(annotation, ast.Name) and annotation.id == "TypeAlias":
                is_type_alias = True
            elif isinstance(annotation, ast.Attribute):
                try:
                    unparsed = ast.unparse(annotation)
                    if "TypeAlias" in unparsed:
                        is_type_alias = True
                except Exception:
                    pass

            if is_type_alias and isinstance(target, ast.Name):
                type_aliases.append(
                    {
                        "name": target.id,
                        "lineno": node.lineno,
                        "value": ast.unparse(node.value) if node.value else None,
                    }
                )

        # --- Constants (UPPER_SNAKE_CASE assignments) ----------------------
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and UPPER_SNAKE_RE.match(target.id):
                    try:
                        value_repr = ast.unparse(node.value)
                    except Exception:
                        value_repr = "<complex>"
                    if len(value_repr) > 120:
                        value_repr = value_repr[:117] + "..."
                    constants.append(
                        {
                            "name": target.id,
                            "lineno": node.lineno,
                            "value_preview": value_repr,
                        }
                    )

    return {
        "file": str(filepath),
        "classes": classes,
        "functions": functions,
        "constants": constants,
        "type_aliases": type_aliases,
    }


# ---------------------------------------------------------------------------
# Aggregation & reporting
# ---------------------------------------------------------------------------


def build_inventory():
    """Walk the source tree and build the full inventory."""
    py_files = sorted(SRC_ROOT.rglob("*.py"))

    by_layer = {layer: [] for layer in LAYERS}
    by_layer["root"] = []

    for fp in py_files:
        layer = _layer_for(fp)
        module_inv = collect_from_file(fp)
        module_inv["layer"] = layer
        module_inv["relative_path"] = str(fp.relative_to(SRC_ROOT))
        by_layer.setdefault(layer, []).append(module_inv)

    return by_layer


def summarise(inventory):
    """Compute summary statistics from the inventory."""
    summary = {}

    # Per-layer totals
    layer_stats = {}
    all_classes = []  # (layer, file, cls_info)
    all_functions = []

    for layer, modules in inventory.items():
        stats = {
            "files": 0,
            "classes": 0,
            "functions": 0,
            "constants": 0,
            "type_aliases": 0,
        }
        for mod in modules:
            stats["files"] += 1
            stats["classes"] += len(mod["classes"])
            stats["functions"] += len(mod["functions"])
            stats["constants"] += len(mod["constants"])
            stats["type_aliases"] += len(mod["type_aliases"])

            for cls in mod["classes"]:
                all_classes.append((layer, mod["relative_path"], cls))
            for fn in mod["functions"]:
                all_functions.append((layer, mod["relative_path"], fn))

        layer_stats[layer] = stats

    summary["per_layer"] = layer_stats

    # Grand totals
    grand = {
        "files": 0,
        "classes": 0,
        "functions": 0,
        "constants": 0,
        "type_aliases": 0,
    }
    for stats in layer_stats.values():
        for k in grand:
            grand[k] += stats[k]
    summary["grand_total"] = grand

    # Top 20 largest classes by LOC
    all_classes.sort(key=lambda t: t[2]["loc"], reverse=True)
    summary["top20_classes_by_loc"] = [
        {
            "layer": layer,
            "file": fpath,
            "class": cls["name"],
            "loc": cls["loc"],
            "public_methods": len(cls["public_methods"]),
            "private_methods": len(cls["private_methods"]),
        }
        for layer, fpath, cls in all_classes[:20]
    ]

    # Top 20 largest functions by LOC
    all_functions.sort(key=lambda t: t[2]["loc"], reverse=True)
    summary["top20_functions_by_loc"] = [
        {
            "layer": layer,
            "file": fpath,
            "function": fn["name"],
            "is_async": fn["is_async"],
            "loc": fn["loc"],
        }
        for layer, fpath, fn in all_functions[:20]
    ]

    # Classes without NAME-001 suffix
    missing_suffix = []
    for layer, fpath, cls in all_classes:
        if not cls["has_name001_suffix"]:
            missing_suffix.append(
                {
                    "layer": layer,
                    "file": fpath,
                    "class": cls["name"],
                    "bases": ", ".join(cls["bases"]) if cls["bases"] else "(none)",
                    "loc": cls["loc"],
                }
            )
    summary["classes_without_name001_suffix"] = missing_suffix

    return summary


def print_summary(summary):
    """Pretty-print the summary to stdout."""
    sep = "=" * 88

    print(sep)
    print("  BIOETL AST INVENTORY SUMMARY")
    print(sep)

    # --- Grand totals ---
    gt = summary["grand_total"]
    print(f"\nGrand Totals:")
    print(f"  Files:        {gt['files']}")
    print(f"  Classes:      {gt['classes']}")
    print(f"  Functions:    {gt['functions']}")
    print(f"  Constants:    {gt['constants']}")
    print(f"  Type Aliases: {gt['type_aliases']}")

    # --- Per-layer ---
    print(f"\n{'-' * 88}")
    print("  PER-LAYER BREAKDOWN")
    print(f"{'-' * 88}")
    header = f"  {'Layer':<20} {'Files':>6} {'Classes':>8} {'Functions':>10} {'Constants':>10} {'TypeAlias':>10}"
    print(header)
    print(f"  {'---':<20} {'---':>6} {'---':>8} {'---':>10} {'---':>10} {'---':>10}")
    for layer in (
        "root",
        "domain",
        "application",
        "infrastructure",
        "composition",
        "interfaces",
    ):
        s = summary["per_layer"].get(layer)
        if s:
            print(
                f"  {layer:<20} {s['files']:>6} {s['classes']:>8} {s['functions']:>10} {s['constants']:>10} {s['type_aliases']:>10}"
            )

    # --- Top 20 classes ---
    print(f"\n{'-' * 88}")
    print("  TOP 20 LARGEST CLASSES (by LOC)")
    print(f"{'-' * 88}")
    print(
        f"  {'#':>3}  {'LOC':>5}  {'Pub':>4} {'Priv':>5}  {'Layer':<16} {'Class':<32} {'File'}"
    )
    for i, entry in enumerate(summary["top20_classes_by_loc"], 1):
        print(
            f"  {i:>3}  {entry['loc']:>5}  {entry['public_methods']:>4} {entry['private_methods']:>5}"
            f"  {entry['layer']:<16} {entry['class']:<32} {entry['file']}"
        )

    # --- Top 20 functions ---
    print(f"\n{'-' * 88}")
    print("  TOP 20 LARGEST FUNCTIONS (by LOC)")
    print(f"{'-' * 88}")
    print(
        f"  {'#':>3}  {'LOC':>5}  {'Async':>5}  {'Layer':<16} {'Function':<35} {'File'}"
    )
    for i, entry in enumerate(summary["top20_functions_by_loc"], 1):
        async_flag = "yes" if entry["is_async"] else "no"
        print(
            f"  {i:>3}  {entry['loc']:>5}  {async_flag:>5}"
            f"  {entry['layer']:<16} {entry['function']:<35} {entry['file']}"
        )

    # --- Classes without NAME-001 suffix ---
    no_suffix = summary["classes_without_name001_suffix"]
    print(f"\n{'-' * 88}")
    print(f"  CLASSES WITHOUT NAME-001 SUFFIX ({len(no_suffix)} total)")
    print(f"{'-' * 88}")
    if no_suffix:
        print(f"  {'Layer':<16} {'Class':<35} {'Bases':<30} {'LOC':>5}  {'File'}")
        for entry in no_suffix:
            bases_str = str(entry["bases"])
            if len(bases_str) > 28:
                bases_str = bases_str[:25] + "..."
            print(
                f"  {entry['layer']:<16} {entry['class']:<35} {bases_str:<30} {entry['loc']:>5}"
                f"  {entry['file']}"
            )
    else:
        print("  (none -- all classes conform)")

    print(f"\n{sep}")
    print(f"  Detailed inventory saved to: {OUTPUT_JSON}")
    print(sep)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    if not SRC_ROOT.is_dir():
        print(f"ERROR: Source root not found: {SRC_ROOT}", file=sys.stderr)
        sys.exit(1)

    print(f"Scanning {SRC_ROOT} ...")
    inventory = build_inventory()

    summary = summarise(inventory)

    # Save detailed JSON
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    output_payload = {
        "summary": summary,
        "inventory": inventory,
    }
    OUTPUT_JSON.write_text(
        json.dumps(output_payload, indent=2, default=str), encoding="utf-8"
    )

    print_summary(summary)


if __name__ == "__main__":
    main()
