#!/usr/bin/env python3
"""
cleanup_consolidate.py — Консолидированный аудит артефактов и кода проекта.

Назначение:
- поиск .pyc, __pycache__ и временных файлов (логика согласована с cleanup_project.py);
- анализ YAML-конфигов на неиспользуемость (отсутствие ссылок в коде/конфигах);
- поиск дубликатов функций в утилитарных модулях (AST-сканирование);
- анализ неиспользуемых импортов (AST + текстовая проверка);
- анализ неиспользуемых зависимостей по pyproject.toml и фактическим импортам.

Режимы:
- dry-run (по умолчанию) — только отчёт;
- --apply — удаляет найденные .pyc/__pycache__/temp файлы.
"""

from __future__ import annotations

import ast
import fnmatch
import os
import re
import shutil
import tomllib
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path

import typer
import yaml

app = typer.Typer(add_completion=False)

PROJECT_ROOT = Path(__file__).resolve().parents[2]

PYTHON_CACHE_DIRS: tuple[str, ...] = ("__pycache__",)
COMPILED_PATTERNS: tuple[str, ...] = ("*.pyc", "*.pyo")
TEMP_PATTERNS: tuple[str, ...] = ("*.tmp", "*.temp", "*.bak")

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
}

DEPENDENCY_IMPORT_ALIASES: dict[str, str] = {
    "pyyaml": "yaml",
    "python-dotenv": "dotenv",
    "pydantic-settings": "pydantic_settings",
    "prometheus-client": "prometheus_client",
}


@dataclass(frozen=True)
class CleanupTarget:
    path: Path
    category: str


@dataclass(frozen=True)
class FunctionOccurrence:
    path: Path
    name: str
    lineno: int


@dataclass(frozen=True)
class UnusedImport:
    path: Path
    name: str
    lineno: int
    module: str | None


def iter_files(root: Path, suffixes: tuple[str, ...]) -> Iterator[Path]:
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


def iter_all_files(root: Path) -> Iterator[Path]:
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if name not in SKIP_DIRS and not name.startswith(".")
        ]
        for filename in filenames:
            if filename.startswith("."):
                continue
            yield Path(dirpath) / filename


def find_cache_targets(root: Path) -> list[CleanupTarget]:
    targets: list[CleanupTarget] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            name
            for name in dirnames
            if name not in SKIP_DIRS and not name.startswith(".")
        ]
        for dirname in list(dirnames):
            if dirname in PYTHON_CACHE_DIRS:
                targets.append(
                    CleanupTarget(
                        path=Path(dirpath) / dirname,
                        category="python_cache_dir",
                    )
                )
        for filename in filenames:
            full_path = Path(dirpath) / filename
            if any(fnmatch.fnmatch(filename, pattern) for pattern in COMPILED_PATTERNS):
                targets.append(
                    CleanupTarget(
                        path=full_path,
                        category="compiled_file",
                    )
                )
            if any(fnmatch.fnmatch(filename, pattern) for pattern in TEMP_PATTERNS):
                targets.append(
                    CleanupTarget(
                        path=full_path,
                        category="temp_file",
                    )
                )
    return targets


def load_reference_texts(root: Path, exclude: Path | None = None) -> list[str]:
    texts: list[str] = []
    for path in iter_files(root, (".py", ".yaml", ".yml")):
        if exclude and path.resolve() == exclude.resolve():
            continue
        try:
            texts.append(path.read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            continue
    return texts


def extract_pipeline_name(path: Path) -> str | None:
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(payload, dict):
        return None
    pipeline = payload.get("pipeline")
    if isinstance(pipeline, dict):
        name = pipeline.get("name")
        if isinstance(name, str):
            return name
    return None


def find_unused_yaml_configs(root: Path) -> list[Path]:
    configs_root = root / "configs"
    if not configs_root.exists():
        return []
    unused: list[Path] = []
    for path in iter_files(configs_root, (".yaml", ".yml")):
        references = load_reference_texts(root, exclude=path)
        filename = path.name
        stem = path.stem
        pipeline_name = extract_pipeline_name(path)
        tokens = [filename, stem]
        if pipeline_name:
            tokens.append(pipeline_name)
        if not any(any(token in text for text in references) for token in tokens):
            unused.append(path)
    return unused


def is_utility_module(path: Path) -> bool:
    name = path.name.lower()
    parts = [part.lower() for part in path.parts]
    return "utils" in parts or "util" in parts or "utils" in name or "util" in name


def normalize_function_node(node: ast.AST) -> str:
    node_copy = ast.fix_missing_locations(ast.parse("pass").body[0])
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        node_copy = ast.FunctionDef(
            name="__FUNCTION__",
            args=node.args,
            body=node.body,
            decorator_list=node.decorator_list,
            returns=node.returns,
            type_comment=node.type_comment,
        )
        if isinstance(node, ast.AsyncFunctionDef):
            node_copy = ast.AsyncFunctionDef(
                name="__FUNCTION__",
                args=node.args,
                body=node.body,
                decorator_list=node.decorator_list,
                returns=node.returns,
                type_comment=node.type_comment,
            )
    return ast.dump(node_copy, include_attributes=False)


def find_duplicate_functions(root: Path) -> dict[str, list[FunctionOccurrence]]:
    occurrences: dict[str, list[FunctionOccurrence]] = {}
    for path in iter_files(root / "src", (".py",)):
        if not is_utility_module(path):
            continue
        try:
            content = path.read_text(encoding="utf-8")
            tree = ast.parse(content)
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                signature = normalize_function_node(node)
                entry = FunctionOccurrence(
                    path=path,
                    name=node.name,
                    lineno=node.lineno,
                )
                occurrences.setdefault(signature, []).append(entry)
    return {
        signature: entries
        for signature, entries in occurrences.items()
        if len(entries) > 1
    }


def collect_used_names(tree: ast.AST) -> set[str]:
    return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def extract_imports(tree: ast.AST) -> list[tuple[str, int, str | None]]:
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


def find_unused_imports(
    paths: Iterable[Path],
) -> tuple[list[UnusedImport], dict[Path, int]]:
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
            name_in_text = re.search(rf"\\b{re.escape(name)}\\b", content) is not None
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
    return re.sub(r"[-_.]+", "-", value.strip().lower())


def collect_imported_modules(paths: Iterable[Path]) -> set[str]:
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


def summarize_module_stats(
    unused_imports_per_file: dict[Path, int],
    duplicate_functions: dict[str, list[FunctionOccurrence]],
) -> list[tuple[Path, int, int]]:
    duplicates_per_file: dict[Path, int] = {}
    for entries in duplicate_functions.values():
        for entry in entries:
            duplicates_per_file[entry.path] = duplicates_per_file.get(entry.path, 0) + 1
    modules = set(unused_imports_per_file) | set(duplicates_per_file)
    summary: list[tuple[Path, int, int]] = []
    for path in sorted(modules):
        summary.append(
            (
                path,
                unused_imports_per_file.get(path, 0),
                duplicates_per_file.get(path, 0),
            )
        )
    return summary


def format_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


@app.command()
def main(
    apply: bool = typer.Option(
        False,
        "--apply",
        help="Применить удаление найденных .pyc/__pycache__/temp файлов.",
    ),
    root: Path = typer.Option(
        PROJECT_ROOT,
        "--root",
        help="Корень репозитория для анализа.",
    ),
) -> None:
    """Запуск консолидированного аудита очистки и зависимостей."""
    dry_run = not apply
    root = root.resolve()
    typer.echo("=== Cleanup Consolidate Report ===")
    typer.echo(f"Root: {root}")
    typer.echo(f"Mode: {'dry-run' if dry_run else 'apply'}")

    cache_targets = find_cache_targets(root)
    unused_yaml = find_unused_yaml_configs(root)

    duplicate_functions = find_duplicate_functions(root)
    python_paths = list(iter_files(root / "src", (".py",)))
    python_paths.extend(iter_files(root / "scripts", (".py",)))
    python_paths.extend(iter_files(root / "tests", (".py",)))
    unused_imports, unused_imports_per_file = find_unused_imports(python_paths)

    unused_deps = find_unused_dependencies(root, root / "pyproject.toml")

    typer.echo("\n-- Очистка артефактов --")
    typer.echo(f"Кандидатов: {len(cache_targets)}")
    if cache_targets:
        for target in cache_targets:
            typer.echo(f"  - {format_path(target.path, root)} [{target.category}]")
    errors: list[str] = []
    if apply and cache_targets:
        errors = delete_targets(cache_targets)
        if errors:
            typer.echo("Ошибки при удалении:")
            for err in errors:
                typer.echo(f"  - {err}")

    typer.echo("\n-- YAML конфиги без ссылок --")
    typer.echo(f"Кандидатов: {len(unused_yaml)}")
    for path in unused_yaml:
        typer.echo(f"  - {format_path(path, root)}")

    typer.echo("\n-- Дубликаты функций (утилитарные модули) --")
    typer.echo(f"Групп дубликатов: {len(duplicate_functions)}")
    for signature, entries in duplicate_functions.items():
        typer.echo(f"  - Сигнатура: {signature[:120]}...")
        for entry in entries:
            typer.echo(
                f"      * {format_path(entry.path, root)}:{entry.lineno} ({entry.name})"
            )

    typer.echo("\n-- Неиспользуемые импорты --")
    typer.echo(f"Кандидатов: {len(unused_imports)}")
    for entry in unused_imports:
        module_display = f" from {entry.module}" if entry.module else ""
        typer.echo(
            f"  - {format_path(entry.path, root)}:{entry.lineno} {entry.name}{module_display}"
        )

    typer.echo("\n-- Неиспользуемые зависимости (pyproject.toml) --")
    typer.echo(f"Кандидатов: {len(unused_deps)}")
    for dep in unused_deps:
        typer.echo(f"  - {dep}")

    typer.echo("\n-- Статистика по модулям --")
    module_stats = summarize_module_stats(unused_imports_per_file, duplicate_functions)
    typer.echo(f"Модулей с находками: {len(module_stats)}")
    for path, unused_count, duplicate_count in module_stats:
        typer.echo(
            f"  - {format_path(path, root)}: imports={unused_count}, duplicates={duplicate_count}"
        )

    typer.echo("\n=== Итог ===")
    typer.echo(
        " | ".join(
            [
                f"артефактов={len(cache_targets)}",
                f"yaml_unused={len(unused_yaml)}",
                f"dup_funcs={len(duplicate_functions)}",
                f"unused_imports={len(unused_imports)}",
                f"unused_deps={len(unused_deps)}",
            ]
        )
    )
    if dry_run:
        typer.echo("Dry-run завершён: файловая система не изменялась.")
    else:
        typer.echo("Применение завершено.")
        if errors:
            typer.echo("Есть ошибки удаления. См. список выше.")


if __name__ == "__main__":
    app()
