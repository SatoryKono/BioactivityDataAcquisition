#!/usr/bin/env python3
"""
cleanup_consolidation.py — безопасная консолидация и уборка проекта.

Функции:
- удаление __pycache__ и *.pyc/*.pyo (dry-run по умолчанию);
- удаление помеченных временных файлов (если есть);
- перемещение/удаление устаревших модулей после консолидации;
- массовое обновление импортов по карте замен.
"""

from __future__ import annotations

import json
import logging
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable

import typer
import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LOG_DIR = PROJECT_ROOT / "reports" / "cleanup_consolidation"

EXCLUDED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "site",
    "data",
    "reports",
    "__pycache__",
}

PYTHON_CACHE_DIRS = ("__pycache__",)
COMPILED_PATTERNS = ("*.pyc", "*.pyo")
TEMP_MARKED_PATTERNS = (
    "*.tmp",
    "*.temp",
    "*.bak",
    "*.swp",
    "*.swo",
    "*.orig",
    "*.rej",
    "*~",
)

IMPORTS_DEFAULT_CODE_ROOTS = (
    PROJECT_ROOT / "src",
    PROJECT_ROOT / "scripts",
)

app = typer.Typer(add_completion=False)


@dataclass(frozen=True)
class CleanupTarget:
    path: Path
    category: str
    is_dir: bool


@dataclass(frozen=True)
class ImportRewrite:
    old: str
    new: str


def _configure_logging(log_dir: Path, verbose: bool) -> logging.Logger:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"cleanup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logger = logging.getLogger("cleanup_consolidation")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    stream_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)
    return logger


def _is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def _iter_matching(root: Path, patterns: Iterable[str]) -> Iterable[Path]:
    for pattern in patterns:
        for candidate in root.rglob(pattern):
            if _is_excluded(candidate):
                continue
            yield candidate


def _find_cache_dirs(root: Path) -> list[CleanupTarget]:
    targets: list[CleanupTarget] = []
    for name in PYTHON_CACHE_DIRS:
        for cache_dir in root.rglob(name):
            if cache_dir.is_dir() and not _is_excluded(cache_dir):
                targets.append(
                    CleanupTarget(path=cache_dir, category="pycache", is_dir=True)
                )
    return targets


def _find_compiled_files(root: Path) -> list[CleanupTarget]:
    targets: list[CleanupTarget] = []
    for file_path in _iter_matching(root, COMPILED_PATTERNS):
        if file_path.is_file():
            targets.append(
                CleanupTarget(path=file_path, category="compiled", is_dir=False)
            )
    return targets


def _find_marked_temp_files(root: Path) -> list[CleanupTarget]:
    targets: list[CleanupTarget] = []
    for file_path in _iter_matching(root, TEMP_MARKED_PATTERNS):
        if file_path.is_file():
            targets.append(
                CleanupTarget(path=file_path, category="temp", is_dir=False)
            )
    return targets


def _load_import_rewrites(path: Path) -> list[ImportRewrite]:
    raw_text = path.read_text(encoding="utf-8")
    data = (
        yaml.safe_load(raw_text)
        if path.suffix in {".yml", ".yaml"}
        else json.loads(raw_text)
    )

    rewrites: list[ImportRewrite] = []
    if isinstance(data, dict):
        for old, new in data.items():
            rewrites.append(ImportRewrite(old=str(old), new=str(new)))
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                old = item.get("old")
                new = item.get("new")
                if old and new:
                    rewrites.append(ImportRewrite(old=str(old), new=str(new)))
    return rewrites


def _rewrite_import_line(line: str, rewrite: ImportRewrite) -> tuple[str, int]:
    stripped = line.lstrip()
    prefix_len = len(line) - len(stripped)
    prefix = line[:prefix_len]
    updated = line
    replacements = 0

    if stripped.startswith("from "):
        marker = f"from {rewrite.old}"
        if stripped.startswith(marker):
            remainder = stripped[len(marker):]
            updated = f"{prefix}from {rewrite.new}{remainder}"
            replacements = 1
        elif stripped.startswith(f"from {rewrite.old}."):
            remainder = stripped[len(f"from {rewrite.old}") :]
            updated = f"{prefix}from {rewrite.new}{remainder}"
            replacements = 1
    elif stripped.startswith("import "):
        modules = stripped[len("import ") :].rstrip("\n")
        parts = [part.strip() for part in modules.split(",")]
        new_parts = []
        for part in parts:
            if part == rewrite.old or part.startswith(f"{rewrite.old}."):
                new_parts.append(rewrite.new + part[len(rewrite.old) :])
                replacements += 1
            elif part.startswith(f"{rewrite.old} ") or part.startswith(
                f"{rewrite.old} as "
            ):
                new_parts.append(rewrite.new + part[len(rewrite.old) :])
                replacements += 1
            else:
                new_parts.append(part)
        if replacements:
            updated = f"{prefix}import {', '.join(new_parts)}\n"

    return updated, replacements


def _apply_import_rewrites(content: str, rewrites: list[ImportRewrite]) -> tuple[str, int]:
    if not rewrites:
        return content, 0

    total_replacements = 0
    new_lines: list[str] = []
    for line in content.splitlines(keepends=True):
        updated_line = line
        for rewrite in rewrites:
            updated_line, replacements = _rewrite_import_line(updated_line, rewrite)
            total_replacements += replacements
        new_lines.append(updated_line)
    return "".join(new_lines), total_replacements


def _iter_code_files(code_roots: Iterable[Path]) -> Iterable[Path]:
    for root in code_roots:
        if not root.exists():
            continue
        for file_path in root.rglob("*.py"):
            if _is_excluded(file_path):
                continue
            yield file_path


def _archive_path(base_dir: Path, target: Path) -> Path:
    relative = target.relative_to(PROJECT_ROOT)
    return base_dir / relative


def _load_obsolete_modules(path: Path) -> list[Path]:
    raw_text = path.read_text(encoding="utf-8")
    data = (
        yaml.safe_load(raw_text)
        if path.suffix in {".yml", ".yaml"}
        else json.loads(raw_text)
    )

    modules: list[Path] = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                modules.append(PROJECT_ROOT / item)
    return modules


def _execute_cleanup(
    root: Path,
    apply: bool,
    confirm: bool,
    import_map: Path | None,
    obsolete_modules_file: Path | None,
    delete_obsolete: bool,
    code_roots: tuple[Path, ...],
    logger: logging.Logger,
) -> int:
    targets: list[CleanupTarget] = []
    targets.extend(_find_cache_dirs(root))
    targets.extend(_find_compiled_files(root))
    targets.extend(_find_marked_temp_files(root))

    logger.info("Найдено %d целей для удаления.", len(targets))
    for target in targets:
        logger.info("  [%s] %s", target.category, target.path.relative_to(root))

    if not targets:
        logger.info("Очистка: ничего не найдено.")

    if apply and confirm and targets:
        if not typer.confirm("Подтвердить удаление найденных файлов?"):
            logger.warning("Операция отменена пользователем.")
            return 1

    if apply:
        for target in targets:
            if target.is_dir:
                shutil.rmtree(target.path, ignore_errors=True)
            else:
                try:
                    target.path.unlink()
                except FileNotFoundError:
                    continue
        logger.info("Очистка завершена: удалено %d объектов.", len(targets))
    else:
        logger.info("Dry-run режим: удаление не выполнялось.")

    if obsolete_modules_file:
        obsolete = _load_obsolete_modules(obsolete_modules_file)
        existing = [path for path in obsolete if path.exists()]
        missing = [path for path in obsolete if not path.exists()]

        logger.info(
            "Устаревшие модули: найдено %d, отсутствует %d.",
            len(existing),
            len(missing),
        )
        for path in existing:
            logger.info("  [obsolete] %s", path.relative_to(root))
        for path in missing:
            logger.warning("  [missing] %s", path.relative_to(root))

        if apply and confirm and existing:
            if not typer.confirm("Подтвердить обработку устаревших модулей?"):
                logger.warning("Обработка устаревших модулей отменена.")
                return 1

        if apply and existing:
            if delete_obsolete:
                for path in existing:
                    if path.is_dir():
                        shutil.rmtree(path, ignore_errors=True)
                    else:
                        try:
                            path.unlink()
                        except FileNotFoundError:
                            continue
                logger.info("Удалено устаревших модулей: %d.", len(existing))
            else:
                archive_root = (
                    root
                    / "reports"
                    / "obsolete_modules"
                    / datetime.now().strftime("%Y%m%d_%H%M%S")
                )
                for path in existing:
                    destination = _archive_path(archive_root, path)
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(path), destination)
                    logger.info("  Перемещено: %s -> %s", path, destination)
                logger.info("Устаревшие модули перемещены в %s.", archive_root)
        elif not apply:
            logger.info("Dry-run: обработка устаревших модулей не выполнялась.")
    else:
        logger.info("Файл со списком устаревших модулей не задан. Шаг пропущен.")

    if import_map:
        rewrites = _load_import_rewrites(import_map)
        if not rewrites:
            logger.warning("Карта импортов пуста: %s", import_map)
        else:
            pending_updates: dict[Path, str] = {}
            total_replacements = 0
            for file_path in _iter_code_files(code_roots):
                original = file_path.read_text(encoding="utf-8")
                updated, replacements = _apply_import_rewrites(original, rewrites)
                if replacements:
                    pending_updates[file_path] = updated
                    total_replacements += replacements
                    logger.info(
                        "  [imports] %s (%d)",
                        file_path.relative_to(root),
                        replacements,
                    )
            total_files = len(pending_updates)
            if not total_files:
                logger.info("Импорты: изменений не требуется.")
            elif apply:
                if confirm and not typer.confirm(
                    "Подтвердить массовое обновление импортов?"
                ):
                    logger.warning("Обновление импортов отменено пользователем.")
                else:
                    for file_path, updated in pending_updates.items():
                        file_path.write_text(updated, encoding="utf-8")
                    logger.info(
                        "Импорты обновлены. Файлов: %d, замен: %d.",
                        total_files,
                        total_replacements,
                    )
            else:
                logger.info(
                    "Dry-run: потенциальные изменения импортов. Файлов: %d, замен: %d.",
                    total_files,
                    total_replacements,
                )
    else:
        logger.info("Карта импортов не задана. Шаг пропущен.")

    return 0


@app.callback(invoke_without_command=True)
def cleanup(
    apply: bool = typer.Option(
        False,
        "--apply/--dry-run",
        help="Выполнить изменения (по умолчанию — dry-run)",
    ),
    yes: bool = typer.Option(
        False,
        "--yes",
        help="Пропустить интерактивные подтверждения",
    ),
    import_map: Path | None = typer.Option(
        None,
        "--import-map",
        help="YAML/JSON карта массовых замен импортов",
    ),
    obsolete_modules_file: Path | None = typer.Option(
        None,
        "--obsolete-modules",
        help="YAML/JSON список устаревших модулей для перемещения/удаления",
    ),
    delete_obsolete: bool = typer.Option(
        False,
        "--delete-obsolete",
        help="Удалять устаревшие модули вместо перемещения в архив",
    ),
    code_root: list[Path] = typer.Option(
        [],
        "--code-root",
        help="Дополнительные директории для обновления импортов",
    ),
    verbose: bool = typer.Option(False, "--verbose", help="Подробный лог"),
) -> None:
    """Запуск безопасной консолидационной очистки."""
    logger = _configure_logging(DEFAULT_LOG_DIR, verbose=verbose)
    logger.info("Старт cleanup_consolidation (apply=%s)", apply)

    code_roots = tuple(dict.fromkeys([*IMPORTS_DEFAULT_CODE_ROOTS, *code_root]))
    confirm = not yes
    exit_code = _execute_cleanup(
        root=PROJECT_ROOT,
        apply=apply,
        confirm=confirm,
        import_map=import_map,
        obsolete_modules_file=obsolete_modules_file,
        delete_obsolete=delete_obsolete,
        code_roots=code_roots,
        logger=logger,
    )

    raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
