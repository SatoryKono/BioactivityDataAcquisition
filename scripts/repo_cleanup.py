#!/usr/bin/env python3
"""
repo_cleanup.py — Repository cleanup and consolidation tool.

Purpose:
- Find and remove .pyc, __pycache__, and temporary files
- Identify duplicate report files with inconsistent naming
- Analyze unused imports in Python files
- Check for unused dependencies in pyproject.toml
- Detect duplicate functions in utility modules

Modes:
- dry-run (default) — report only
- --apply — actually delete/move files

Uses Click (project standard per CLAUDE.md) instead of Typer.
"""

from __future__ import annotations

import ast
import fnmatch
import os
import re
import shutil
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Sequence

import click

PROJECT_ROOT = Path(__file__).resolve().parents[1]

# Patterns for cleanup targets
PYTHON_CACHE_DIRS: tuple[str, ...] = ("__pycache__",)
COMPILED_PATTERNS: tuple[str, ...] = ("*.pyc", "*.pyo")
TEMP_PATTERNS: tuple[str, ...] = ("*.tmp", "*.temp", "*.bak")

# Directories to skip during traversal
SKIP_DIRS: set[str] = {
    ".git",
    ".venv",
    "venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".hypothesis",
    ".tox",
    ".eggs",
    "site",
    "data",
    "node_modules",
}

# Known duplicate report file patterns (hyphen vs underscore)
DUPLICATE_REPORT_PATTERNS: list[tuple[str, str]] = [
    ("application-merged.md", "application_merged.md"),
    ("composition-merged.md", "composition_merged.md"),
    ("configs-merged.md", "configs_merged.md"),
    ("documentation-merged.md", "documentation_merged.md"),
    ("domain-merged.md", "domain_merged.md"),
    ("infrastructure-merged.md", "infrastructure_merged.md"),
    ("interfaces-merged.md", "interfaces_merged.md"),
    ("project-structure.md", "project_structure.md"),
]

# Dependency import aliases (package name -> import name)
DEPENDENCY_IMPORT_ALIASES: dict[str, str] = {
    "pyyaml": "yaml",
    "python-dotenv": "dotenv",
    "pydantic-settings": "pydantic_settings",
    "prometheus-client": "prometheus_client",
}


@dataclass(frozen=True)
class CleanupTarget:
    """Represents a file or directory to be cleaned up."""

    path: Path
    category: str
    size_bytes: int = 0


@dataclass(frozen=True)
class DuplicateReport:
    """Represents a pair of duplicate report files."""

    older: Path
    newer: Path
    size_older: int
    size_newer: int


@dataclass(frozen=True)
class UnusedImport:
    """Represents an unused import in a Python file."""

    path: Path
    name: str
    lineno: int
    module: str | None


def iter_files(root: Path, suffixes: tuple[str, ...]) -> Iterator[Path]:
    """Iterate over files with given suffixes, skipping excluded directories."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if name not in SKIP_DIRS and not name.startswith(".")
        ]
        for filename in filenames:
            if filename.startswith("."):
                continue
            if filename.endswith(suffixes):
                yield Path(dirpath) / filename


def find_cache_targets(root: Path) -> list[CleanupTarget]:
    """Find Python cache directories and compiled files."""
    targets: list[CleanupTarget] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if name not in SKIP_DIRS and not name.startswith(".")
        ]
        for dirname in list(dirnames):
            if dirname in PYTHON_CACHE_DIRS:
                cache_path = Path(dirpath) / dirname
                size = get_dir_size(cache_path)
                targets.append(
                    CleanupTarget(
                        path=cache_path,
                        category="python_cache_dir",
                        size_bytes=size,
                    )
                )
        for filename in filenames:
            full_path = Path(dirpath) / filename
            if any(fnmatch.fnmatch(filename, pattern) for pattern in COMPILED_PATTERNS):
                targets.append(
                    CleanupTarget(
                        path=full_path,
                        category="compiled_file",
                        size_bytes=full_path.stat().st_size if full_path.exists() else 0,
                    )
                )
            if any(fnmatch.fnmatch(filename, pattern) for pattern in TEMP_PATTERNS):
                targets.append(
                    CleanupTarget(
                        path=full_path,
                        category="temp_file",
                        size_bytes=full_path.stat().st_size if full_path.exists() else 0,
                    )
                )
    return targets


def get_dir_size(path: Path) -> int:
    """Calculate total size of a directory."""
    total = 0
    try:
        for entry in path.rglob("*"):
            if entry.is_file():
                total += entry.stat().st_size
    except OSError:
        pass
    return total


def find_duplicate_reports(root: Path) -> list[DuplicateReport]:
    """Find duplicate report files with inconsistent naming."""
    reports_dir = root / "reports"
    if not reports_dir.exists():
        return []

    duplicates: list[DuplicateReport] = []
    for older_name, newer_name in DUPLICATE_REPORT_PATTERNS:
        older_path = reports_dir / older_name
        newer_path = reports_dir / newer_name
        if older_path.exists() and newer_path.exists():
            duplicates.append(
                DuplicateReport(
                    older=older_path,
                    newer=newer_path,
                    size_older=older_path.stat().st_size,
                    size_newer=newer_path.stat().st_size,
                )
            )
    return duplicates


def find_temp_root_files(root: Path) -> list[CleanupTarget]:
    """Find temporary files in the repository root."""
    temp_files: list[CleanupTarget] = []
    known_temp_patterns = ["test_output.txt", "*.log", "full_log.txt"]

    for pattern in known_temp_patterns:
        for path in root.glob(pattern):
            if path.is_file():
                temp_files.append(
                    CleanupTarget(
                        path=path,
                        category="temp_root_file",
                        size_bytes=path.stat().st_size,
                    )
                )
    return temp_files


def collect_used_names(tree: ast.AST) -> set[str]:
    """Collect all Name nodes from AST."""
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def extract_imports(tree: ast.AST) -> list[tuple[str, int, str | None]]:
    """Extract all import statements from AST."""
    imports: list[tuple[str, int, str | None]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                alias_name = alias.asname or alias.name.split(".")[0]
                imports.append((alias_name, node.lineno, alias.name))
        elif isinstance(node, ast.ImportFrom):
            for alias in node.names:
                alias_name = alias.asname or alias.name
                imports.append((alias_name, node.lineno, node.module))
    return imports


def find_unused_imports(paths: list[Path]) -> tuple[list[UnusedImport], dict[Path, int]]:
    """Find unused imports in Python files."""
    unused: list[UnusedImport] = []
    per_file: dict[Path, int] = {}

    for path in paths:
        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except (OSError, SyntaxError):
            continue

        used_names = collect_used_names(tree)
        imports = extract_imports(tree)

        for name, lineno, module in imports:
            # Check if name is used (as Name node or in text)
            name_in_text = re.search(rf"\b{re.escape(name)}\b", content) is not None
            if name not in used_names and not name_in_text:
                unused.append(
                    UnusedImport(
                        path=path,
                        name=name,
                        lineno=lineno,
                        module=module,
                    )
                )
                per_file[path] = per_file.get(path, 0) + 1

    return unused, per_file


def parse_dependencies(pyproject_path: Path) -> list[str]:
    """Parse dependencies from pyproject.toml."""
    try:
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    except OSError:
        return []

    project = data.get("project", {})
    dependencies = project.get("dependencies", [])
    if not isinstance(dependencies, list):
        return []

    parsed: list[str] = []
    for entry in dependencies:
        if not isinstance(entry, str):
            continue
        name = entry.split(";")[0].strip()
        name = name.split("[")[0].strip()
        name = re.split(r"[<>=!~ ]", name, maxsplit=1)[0].strip()
        if name:
            parsed.append(name)
    return parsed


def normalize_name(value: str) -> str:
    """Normalize package/module name for comparison."""
    return re.sub(r"[-_.]+", "-", value.strip().lower())


def collect_imported_modules(paths: list[Path]) -> set[str]:
    """Collect all imported module names from Python files."""
    imported: set[str] = set()
    for path in paths:
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.level != 0 or not node.module:
                    continue
                imported.add(node.module.split(".")[0])
    return {normalize_name(name) for name in imported}


def find_unused_dependencies(root: Path, pyproject_path: Path) -> list[str]:
    """Find dependencies that are not imported anywhere in the codebase."""
    dependencies = parse_dependencies(pyproject_path)
    if not dependencies:
        return []

    python_paths = list(iter_files(root / "src", (".py",)))
    python_paths.extend(iter_files(root / "scripts", (".py",)))
    python_paths.extend(iter_files(root / "tests", (".py",)))

    imported_modules = collect_imported_modules(python_paths)
    unused: list[str] = []

    for dep in dependencies:
        normalized = normalize_name(dep)
        alias = DEPENDENCY_IMPORT_ALIASES.get(dep)
        alias_normalized = normalize_name(alias) if alias else None

        if normalized in imported_modules:
            continue
        if alias_normalized and alias_normalized in imported_modules:
            continue
        dep_module = normalize_name(dep.replace("-", "_"))
        if dep_module in imported_modules:
            continue

        unused.append(dep)

    return sorted(unused)


def delete_targets(targets: Sequence[CleanupTarget]) -> list[str]:
    """Delete cleanup targets, returning list of errors."""
    errors: list[str] = []
    for target in targets:
        try:
            if target.path.is_dir():
                shutil.rmtree(target.path)
            else:
                target.path.unlink()
        except OSError as exc:
            errors.append(f"{target.path}: {exc}")
    return errors


def format_size(size_bytes: int) -> str:
    """Format byte size to human-readable string."""
    if size_bytes < 1024:
        return f"{size_bytes}B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f}K"
    else:
        return f"{size_bytes / (1024 * 1024):.1f}M"


def format_path(path: Path, root: Path) -> str:
    """Format path relative to root."""
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


@click.command()
@click.option(
    "--apply",
    is_flag=True,
    default=False,
    help="Apply changes (delete files). Default is dry-run.",
)
@click.option(
    "--root",
    type=click.Path(exists=True, path_type=Path),
    default=PROJECT_ROOT,
    help="Repository root directory.",
)
@click.option(
    "--skip-imports",
    is_flag=True,
    default=False,
    help="Skip unused import analysis (faster).",
)
@click.option(
    "--skip-deps",
    is_flag=True,
    default=False,
    help="Skip unused dependency analysis.",
)
def main(
    apply: bool,
    root: Path,
    skip_imports: bool,
    skip_deps: bool,
) -> None:
    """
    BioETL Repository Cleanup Tool.

    Analyzes the repository for cleanup candidates including:
    - Python cache directories and compiled files
    - Duplicate report files with inconsistent naming
    - Temporary files in repository root
    - Unused imports (optional)
    - Unused dependencies (optional)

    By default runs in dry-run mode (no changes).
    Use --apply to actually delete files.
    """
    dry_run = not apply
    root = root.resolve()

    click.secho("=" * 50, fg="cyan")
    click.secho("BioETL Repository Cleanup Report", fg="cyan", bold=True)
    click.secho("=" * 50, fg="cyan")
    click.echo(f"Root: {root}")
    click.echo(f"Mode: {'dry-run' if dry_run else click.style('APPLY', fg='red', bold=True)}")
    click.echo()

    # 1. Find cache targets
    cache_targets = find_cache_targets(root)
    click.secho("1. Python Cache & Compiled Files", fg="yellow", bold=True)
    click.echo(f"   Found: {len(cache_targets)} items")
    total_cache_size = sum(t.size_bytes for t in cache_targets)
    if cache_targets:
        for target in cache_targets[:10]:  # Show first 10
            click.echo(f"   - {format_path(target.path, root)} [{target.category}] ({format_size(target.size_bytes)})")
        if len(cache_targets) > 10:
            click.echo(f"   ... and {len(cache_targets) - 10} more")
        click.echo(f"   Total size: {format_size(total_cache_size)}")
    click.echo()

    # 2. Find duplicate reports
    duplicate_reports = find_duplicate_reports(root)
    click.secho("2. Duplicate Report Files", fg="yellow", bold=True)
    click.echo(f"   Found: {len(duplicate_reports)} pairs")
    total_dup_size = sum(d.size_older for d in duplicate_reports)
    for dup in duplicate_reports:
        click.echo(f"   - {dup.older.name} ({format_size(dup.size_older)}) -> REMOVE")
        click.echo(f"     {dup.newer.name} ({format_size(dup.size_newer)}) -> KEEP")
    if duplicate_reports:
        click.echo(f"   Space to free: {format_size(total_dup_size)}")
    click.echo()

    # 3. Find temp root files
    temp_root_files = find_temp_root_files(root)
    click.secho("3. Temporary Root Files", fg="yellow", bold=True)
    click.echo(f"   Found: {len(temp_root_files)} files")
    for target in temp_root_files:
        click.echo(f"   - {target.path.name} ({format_size(target.size_bytes)})")
    click.echo()

    # 4. Unused imports (optional)
    unused_imports: list[UnusedImport] = []
    if not skip_imports:
        click.secho("4. Unused Imports Analysis", fg="yellow", bold=True)
        python_paths = list(iter_files(root / "src", (".py",)))
        unused_imports, per_file = find_unused_imports(python_paths)
        click.echo(f"   Found: {len(unused_imports)} unused imports")
        if unused_imports:
            for entry in unused_imports[:5]:
                module_display = f" from {entry.module}" if entry.module else ""
                click.echo(f"   - {format_path(entry.path, root)}:{entry.lineno} {entry.name}{module_display}")
            if len(unused_imports) > 5:
                click.echo(f"   ... and {len(unused_imports) - 5} more")
    else:
        click.secho("4. Unused Imports Analysis (skipped)", fg="yellow", bold=True)
    click.echo()

    # 5. Unused dependencies (optional)
    unused_deps: list[str] = []
    if not skip_deps:
        click.secho("5. Unused Dependencies Analysis", fg="yellow", bold=True)
        unused_deps = find_unused_dependencies(root, root / "pyproject.toml")
        click.echo(f"   Found: {len(unused_deps)} unused dependencies")
        for dep in unused_deps:
            click.echo(f"   - {dep}")
    else:
        click.secho("5. Unused Dependencies Analysis (skipped)", fg="yellow", bold=True)
    click.echo()

    # Summary
    click.secho("=" * 50, fg="cyan")
    click.secho("Summary", fg="cyan", bold=True)
    click.secho("=" * 50, fg="cyan")
    click.echo(f"Cache targets: {len(cache_targets)} ({format_size(total_cache_size)})")
    click.echo(f"Duplicate reports: {len(duplicate_reports)} pairs ({format_size(total_dup_size)})")
    click.echo(f"Temp root files: {len(temp_root_files)}")
    click.echo(f"Unused imports: {len(unused_imports)}")
    click.echo(f"Unused dependencies: {len(unused_deps)}")
    click.echo()

    # Apply changes if requested
    if apply:
        click.secho("Applying changes...", fg="red", bold=True)
        errors: list[str] = []

        # Delete cache targets
        if cache_targets:
            click.echo("Deleting cache targets...")
            errors.extend(delete_targets(cache_targets))

        # Delete older duplicate reports
        if duplicate_reports:
            click.echo("Deleting older duplicate reports...")
            dup_targets = [
                CleanupTarget(path=d.older, category="duplicate_report", size_bytes=d.size_older)
                for d in duplicate_reports
            ]
            errors.extend(delete_targets(dup_targets))

        # Delete temp root files
        if temp_root_files:
            click.echo("Deleting temp root files...")
            errors.extend(delete_targets(temp_root_files))

        if errors:
            click.secho("Errors occurred:", fg="red")
            for err in errors:
                click.echo(f"  - {err}")
        else:
            click.secho("All changes applied successfully!", fg="green")
    else:
        click.secho("Dry-run complete. No changes made.", fg="green")
        click.echo("Use --apply to actually delete files.")


if __name__ == "__main__":
    main()
