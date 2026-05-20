#!/usr/bin/env python3
"""Shared first-party import graph helpers for QA inventory reports."""

from __future__ import annotations

import ast
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class PackageScan:
    """One first-party package tree to scan."""

    label: str
    root: Path
    module_prefix: str


@dataclass(frozen=True)
class ParsedModule:
    """Parsed first-party Python module ready for repeated import-graph scans."""

    scan_label: str
    rel_path: str
    candidate_targets: tuple[str, ...]
    exact_import_usage: tuple[tuple[str, tuple[str, ...]], ...]


def default_scan_roots(repo_root: Path) -> tuple[PackageScan, ...]:
    """Return the canonical first-party scan roots."""
    return (
        PackageScan("src", repo_root / "src" / "bioetl", "bioetl"),
        PackageScan("tests", repo_root / "tests", "tests"),
    )


def _iter_python_modules(scan: PackageScan) -> list[tuple[str, Path]]:
    if not scan.root.exists():
        return []

    modules: list[tuple[str, Path]] = []
    for py_file in sorted(scan.root.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        rel_path = py_file.relative_to(scan.root)
        if py_file.name == "__init__.py":
            rel_parts = rel_path.parent.parts
        else:
            rel_parts = rel_path.with_suffix("").parts
        module_name = ".".join(
            [scan.module_prefix, *rel_parts] if rel_parts else [scan.module_prefix]
        )
        modules.append((module_name, py_file))
    return modules


def _collect_existing_modules(scan: PackageScan) -> frozenset[str]:
    return frozenset(module_name for module_name, _ in _iter_python_modules(scan))


@lru_cache(maxsize=None)
def _collect_parsed_modules(repo_root_str: str) -> tuple[ParsedModule, ...]:
    """Parse first-party Python modules once per repo path for reuse across checks."""
    repo_root = Path(repo_root_str)
    scans = default_scan_roots(repo_root)
    existing_modules = _collect_existing_modules(scans[0])
    parsed_modules: list[ParsedModule] = []

    for scan in scans:
        for importer_module, py_file in _iter_python_modules(scan):
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except (OSError, SyntaxError, UnicodeDecodeError):
                continue
            candidate_targets: set[str] = set()
            exact_import_usage: dict[str, set[str]] = defaultdict(set)
            for node in ast.walk(tree):
                for target_module in _iter_candidate_import_targets(
                    existing_modules=existing_modules,
                    importer_module=importer_module,
                    node=node,
                ):
                    candidate_targets.add(target_module)

                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name.startswith("bioetl."):
                            exact_import_usage[alias.name].add("<module>")
                elif isinstance(node, ast.ImportFrom):
                    base_module = _resolve_relative_module(
                        importer_module=importer_module,
                        module=node.module,
                        level=node.level,
                    )
                    if not base_module or not base_module.startswith("bioetl."):
                        continue
                    for alias in node.names:
                        exact_import_usage[base_module].add(alias.name)
            parsed_modules.append(
                ParsedModule(
                    scan_label=scan.label,
                    rel_path=py_file.relative_to(repo_root).as_posix(),
                    candidate_targets=tuple(sorted(candidate_targets)),
                    exact_import_usage=tuple(
                        (module_name, tuple(sorted(imported_names)))
                        for module_name, imported_names in sorted(
                            exact_import_usage.items()
                        )
                    ),
                )
            )

    return tuple(parsed_modules)


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


def collect_bioetl_importers(
    repo_root: Path,
) -> dict[str, dict[str, tuple[str, ...]]]:
    """Collect first-party importers for every ``bioetl.*`` module."""
    scans = default_scan_roots(repo_root)
    src_scan = scans[0]
    existing_modules = _collect_existing_modules(src_scan)
    importers: dict[str, dict[str, set[str]]] = {
        module_name: {"src": set(), "tests": set()} for module_name in existing_modules
    }

    for parsed_module in _collect_parsed_modules(str(repo_root.resolve())):
        for target_module in parsed_module.candidate_targets:
            if target_module in importers:
                importers[target_module][parsed_module.scan_label].add(
                    parsed_module.rel_path
                )

    return {
        module_name: {
            "src": tuple(sorted(paths["src"])),
            "tests": tuple(sorted(paths["tests"])),
        }
        for module_name, paths in sorted(importers.items())
    }


def collect_exact_module_import_usage(
    repo_root: Path, target_module: str
) -> dict[str, dict[str, tuple[str, ...]]]:
    """Collect exact first-party import usage for one target module.

    The returned mapping is keyed first by scan label (`src` / `tests`) and then
    by importer path. Each importer path maps to the tuple of imported names used
    from the target module. Direct ``import <module>`` statements are recorded as
    ``"<module>"``.
    """

    scans = default_scan_roots(repo_root)
    usage: dict[str, dict[str, set[str]]] = {
        scan.label: defaultdict(set) for scan in scans
    }

    for parsed_module in _collect_parsed_modules(str(repo_root.resolve())):
        exact_usage = dict(parsed_module.exact_import_usage)
        if target_module not in exact_usage:
            continue
        for imported_name in exact_usage[target_module]:
            usage[parsed_module.scan_label][parsed_module.rel_path].add(imported_name)

    return {
        label: {
            rel_path: tuple(sorted(imported_names))
            for rel_path, imported_names in sorted(path_map.items())
        }
        for label, path_map in usage.items()
    }


def find_public_private_twin_modules(repo_root: Path) -> list[dict[str, str]]:
    """Return sibling ``_private.py``/``public.py`` first-party module pairs."""
    src_root = repo_root / "src" / "bioetl"
    src_scan = PackageScan("src", src_root, "bioetl")
    module_name_by_path = {
        path: module_name for module_name, path in _iter_python_modules(src_scan)
    }
    pairs: list[dict[str, str]] = []

    for py_file in sorted(src_root.rglob("_*.py")):
        if py_file.name == "__init__.py":
            continue
        public_file = py_file.with_name(py_file.name[1:])
        if not public_file.exists():
            continue
        private_module = module_name_by_path.get(py_file)
        public_module = module_name_by_path.get(public_file)
        if private_module is None or public_module is None:
            continue
        pairs.append(
            {
                "private_path": py_file.relative_to(repo_root).as_posix(),
                "public_path": public_file.relative_to(repo_root).as_posix(),
                "private_module": private_module,
                "public_module": public_module,
            }
        )

    return pairs


def collect_zero_import_bioetl_modules(repo_root: Path) -> list[dict[str, object]]:
    """Return repo-wide ``bioetl`` modules with zero first-party static importers."""
    scans = default_scan_roots(repo_root)
    src_scan = scans[0]
    importer_map = collect_bioetl_importers(repo_root)
    zero_import_modules: list[dict[str, object]] = []

    for module_name, py_file in _iter_python_modules(src_scan):
        if py_file.name == "__init__.py":
            continue
        importer_entry = importer_map.get(module_name, {"src": (), "tests": ()})
        src_importers = tuple(importer_entry.get("src", ()))
        test_importers = tuple(importer_entry.get("tests", ()))
        if src_importers or test_importers:
            continue
        zero_import_modules.append(
            {
                "module_name": module_name,
                "path": py_file.relative_to(repo_root).as_posix(),
                "is_private_module": py_file.name.startswith("_"),
                "src_importer_count": 0,
                "test_importer_count": 0,
            }
        )

    return zero_import_modules
