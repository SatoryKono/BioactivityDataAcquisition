#!/usr/bin/env python3
"""
BioETL Structure Audit Tool.

Проверяет соответствие структуры проекта File Policy (03-file-policy.md).

Usage:
    python scripts/audit_structure.py [--json] [--strict]

Flags:
    --json    Output results in JSON format
    --strict  Exit with code 1 on SHOULD violations too (default: only MUST)

Aligned with RULES.md v5.24 (2026-03-03)
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess  # nosec B404
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from scripts.engineering.repo._root_governance import load_root_governance_policy

# Configure logging for CLI output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# =============================================================================
# Configuration: Allowed directories and paths
# =============================================================================

# Local untracked directories tolerated by structural audit.
LOCAL_TOLERATED_ROOT_DIRS: set[str] = {
    ".import_linter_cache",
    ".trae",
    ".windsurf",
}

# Directories that SHOULD NOT be committed (generated or temp)
GENERATED_DIRS: set[str] = {
    "site",  # MkDocs output (in .gitignore)
    "build",
    "dist",
    "htmlcov",
    "logs",
    "node_modules",
    "output",
    "test-output",
    "MagicMock",
    ".codex_tmp",
    ".python-user",
}

# Technical directories (auto-generated, always excluded)
TECHNICAL_DIRS: set[str] = {
    ".venv",
    "venv",
    ".git",
    ".worktrees",
    ".rollback",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".eggs",
    ".benchmarks",
    ".hypothesis",
}
PRUNED_RECURSION_DIRS: frozenset[str] = frozenset(
    TECHNICAL_DIRS
    | GENERATED_DIRS
    | LOCAL_TOLERATED_ROOT_DIRS
    | {"data", "docs", "configs"}
)
PRUNED_SUBTREE_DIRS: frozenset[str] = frozenset(
    TECHNICAL_DIRS | GENERATED_DIRS | LOCAL_TOLERATED_ROOT_DIRS
)

# Allowed Python paths
ALLOWED_PYTHON_PATHS: tuple[str, ...] = (
    "src/",
    "tests/",
    "scripts/",
    "docs/00-project/ai/skills/",  # Agent skills scripts
    ".ai/mcp/",  # MCP server implementations
)

# Allowed root-level Python files
ALLOWED_ROOT_PY_FILES: set[str] = {
    "setup.py",
    "conftest.py",
}
CATALOG_ALLOWED_PYTHON_ROOT_SECTIONS: tuple[str, ...] = (
    "root_tooling_roots",
    "test_support_roots",
)

# Required layers in src/bioetl (per CLAUDE.md §2)
REQUIRED_BIOETL_LAYERS: set[str] = {
    "domain",
    "application",
    "infrastructure",
    "interfaces",
    "composition",  # DI container layer (per CLAUDE.md)
}


# =============================================================================
# Violation Data Model
# =============================================================================


@dataclass
class Violation:
    """Нарушение политики структуры проекта."""

    category: str
    path: str
    message: str
    severity: str  # MUST | SHOULD

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for JSON output."""
        return {
            "category": self.category,
            "path": self.path,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass
class AuditResult:
    """Результат аудита структуры."""

    violations: list[Violation] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def must_violations(self) -> list[Violation]:
        """MUST violations (блокеры)."""
        return [v for v in self.violations if v.severity == "MUST"]

    @property
    def should_violations(self) -> list[Violation]:
        """SHOULD violations (рекомендации)."""
        return [v for v in self.violations if v.severity == "SHOULD"]

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output."""
        return {
            "violations": [v.to_dict() for v in self.violations],
            "warnings": self.warnings,
            "summary": {
                "must_count": len(self.must_violations),
                "should_count": len(self.should_violations),
                "total": len(self.violations),
            },
        }


# =============================================================================
# Audit Logic
# =============================================================================


def _is_technical_or_generated(name: str) -> bool:
    """Check if directory is technical/generated."""
    if name in TECHNICAL_DIRS or name in GENERATED_DIRS:
        return True
    if name.endswith(".egg-info"):
        return True
    return False


def _has_path_segment(path: Path, segments: set[str]) -> bool:
    """Check whether a path contains any segment from a set."""
    return any(part in segments for part in path.parts)


def _walk_python_files(
    root: Path,
    *,
    prune_dirs: frozenset[str],
) -> Iterator[Path]:
    """Yield Python files while pruning slow or policy-irrelevant subtrees."""
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in prune_dirs]
        base = Path(dirpath)
        for filename in filenames:
            if filename.endswith(".py"):
                yield base / filename


def _tracked_python_files(project_root: Path) -> list[Path] | None:
    """Return tracked Python files when the project is inside a git worktree."""
    if not (project_root / ".git").exists():
        return None
    try:
        completed = subprocess.run(  # nosec
            ["git", "-C", str(project_root), "ls-files", "-z"],
            check=True,
            capture_output=True,
            text=False,
        )
    except (OSError, subprocess.CalledProcessError):
        return None
    return [
        project_root / rel_path
        for rel_path in completed.stdout.decode("utf-8", errors="replace").split("\0")
        if rel_path.endswith(".py")
    ]


def _iter_project_python_files(project_root: Path) -> Iterator[Path]:
    """Yield project Python files from git when possible, else from filesystem."""
    tracked_files = _tracked_python_files(project_root)
    if tracked_files is not None:
        yield from tracked_files
        return
    yield from _walk_python_files(
        project_root,
        prune_dirs=PRUNED_RECURSION_DIRS,
    )


def _allowed_python_prefixes(root_policy) -> tuple[str, ...]:
    """Return static and catalog-ratified Python roots."""
    prefixes = list(ALLOWED_PYTHON_PATHS)
    for section_name in CATALOG_ALLOWED_PYTHON_ROOT_SECTIONS:
        section = root_policy.catalog.get(section_name)
        if not isinstance(section, dict):
            continue
        for entry in section.get("approved_roots", []):
            if not isinstance(entry, dict):
                continue
            path = entry.get("path")
            if isinstance(path, str) and path:
                prefixes.append(f"{path.rstrip('/')}/")
    return tuple(dict.fromkeys(prefixes))


def _check_root_directories(
    project_root: Path,
    *,
    approved_root_dirs: frozenset[str],
) -> Iterator[Violation]:
    """Проверка корневых каталогов против whitelist."""
    for item in project_root.iterdir():
        if not item.is_dir():
            continue

        name = item.name

        # Local dev/tooling directories are tolerated when untracked.
        if name in LOCAL_TOLERATED_ROOT_DIRS:
            continue

        # Skip technical directories
        if _is_technical_or_generated(name):
            continue

        # Check hidden directories
        if name.startswith("."):
            if name not in approved_root_dirs:
                yield Violation(
                    category="ROOT_DIR_HIDDEN",
                    path=str(item.relative_to(project_root)),
                    message=f"Неразрешённая скрытая папка в корне: {name}",
                    severity="SHOULD",
                )
        # Check regular directories
        elif name not in approved_root_dirs:
            yield Violation(
                category="ROOT_DIR",
                path=str(item.relative_to(project_root)),
                message=f"Неразрешённая папка в корне: {name}",
                severity="MUST",
            )


def _check_python_locations(
    project_root: Path,
    *,
    allowed_python_prefixes: tuple[str, ...],
) -> Iterator[Violation]:
    """Проверка расположения Python-файлов."""
    for py_file in _iter_project_python_files(project_root):
        rel_path = py_file.relative_to(project_root)
        posix_path = rel_path.as_posix()

        # Skip technical directories
        if _has_path_segment(rel_path, TECHNICAL_DIRS):
            continue
        if _has_path_segment(rel_path, GENERATED_DIRS):
            continue

        # Check if in allowed location
        is_allowed = any(posix_path.startswith(p) for p in allowed_python_prefixes)
        is_root_allowed = (
            py_file.parent == project_root and py_file.name in ALLOWED_ROOT_PY_FILES
        )

        if not is_allowed and not is_root_allowed:
            yield Violation(
                category="PYTHON_LOCATION",
                path=str(rel_path),
                message=f"Python-файл в недопустимом месте: {rel_path}",
                severity="MUST",
            )


def _check_bioetl_layers(project_root: Path) -> Iterator[Violation]:
    """Проверка структуры слоёв src/bioetl/."""
    bioetl_path = project_root / "src" / "bioetl"
    if not bioetl_path.exists():
        yield Violation(
            category="LAYER_MISSING",
            path="src/bioetl/",
            message="Директория src/bioetl/ не существует",
            severity="MUST",
        )
        return

    existing_layers = {
        d.name
        for d in bioetl_path.iterdir()
        if d.is_dir() and not d.name.startswith("_")
    }

    # Check for missing required layers
    missing = REQUIRED_BIOETL_LAYERS - existing_layers
    for layer in sorted(missing):
        yield Violation(
            category="LAYER_MISSING",
            path=f"src/bioetl/{layer}/",
            message=f"Отсутствует обязательный слой: {layer}",
            severity="MUST",
        )

    # Check for extra layers
    extra = existing_layers - REQUIRED_BIOETL_LAYERS
    for layer in sorted(extra):
        yield Violation(
            category="LAYER_EXTRA",
            path=f"src/bioetl/{layer}/",
            message=f"Неожиданный каталог в src/bioetl/: {layer}",
            severity="SHOULD",
        )


def _check_no_python_in_docs(project_root: Path) -> Iterator[Violation]:
    """Проверка отсутствия Python-кода в docs/."""
    docs_path = project_root / "docs"
    if not docs_path.exists():
        return

    tracked_files = _tracked_python_files(project_root)
    python_files = (
        tracked_files
        if tracked_files is not None
        else _walk_python_files(docs_path, prune_dirs=PRUNED_SUBTREE_DIRS)
    )
    for py_file in python_files:
        if tracked_files is not None and not py_file.is_relative_to(docs_path):
            continue
        rel_path = py_file.relative_to(project_root)
        posix_path = rel_path.as_posix()

        # Allow scripts in docs/00-project/ai/skills/
        if posix_path.startswith("docs/00-project/ai/skills/"):
            continue

        yield Violation(
            category="DOCS_CODE",
            path=str(rel_path),
            message="Python-код в docs/ запрещён (кроме docs/00-project/ai/skills/)",
            severity="MUST",
        )


def _check_no_python_in_configs(project_root: Path) -> Iterator[Violation]:
    """Проверка отсутствия Python-кода в configs/."""
    configs_path = project_root / "configs"
    if not configs_path.exists():
        return

    tracked_files = _tracked_python_files(project_root)
    python_files = (
        tracked_files
        if tracked_files is not None
        else _walk_python_files(configs_path, prune_dirs=PRUNED_SUBTREE_DIRS)
    )
    for py_file in python_files:
        if tracked_files is not None and not py_file.is_relative_to(configs_path):
            continue
        yield Violation(
            category="CONFIGS_CODE",
            path=str(py_file.relative_to(project_root)),
            message="Python-код в configs/ запрещён",
            severity="MUST",
        )


def _check_no_python_in_data(project_root: Path) -> Iterator[Violation]:
    """Проверка отсутствия Python-кода в data/."""
    data_path = project_root / "data"
    if not data_path.exists():
        return

    tracked_files = _tracked_python_files(project_root)
    python_files = (
        tracked_files
        if tracked_files is not None
        else _walk_python_files(data_path, prune_dirs=PRUNED_SUBTREE_DIRS)
    )
    for py_file in python_files:
        if tracked_files is not None and not py_file.is_relative_to(data_path):
            continue
        yield Violation(
            category="DATA_CODE",
            path=str(py_file.relative_to(project_root)),
            message="Python-код в data/ запрещён",
            severity="MUST",
        )


def run_audit(project_root: Path) -> AuditResult:
    """Выполнить полный аудит структуры проекта."""
    result = AuditResult()
    root_policy = load_root_governance_policy(project_root)
    allowed_python_prefixes = _allowed_python_prefixes(root_policy)

    # Run all checks
    checks = [
        lambda root: _check_root_directories(
            root,
            approved_root_dirs=root_policy.approved_root_directories,
        ),
        lambda root: _check_python_locations(
            root,
            allowed_python_prefixes=allowed_python_prefixes,
        ),
        _check_bioetl_layers,
        _check_no_python_in_docs,
        _check_no_python_in_configs,
        _check_no_python_in_data,
    ]

    for check in checks:
        result.violations.extend(check(project_root))

    return result


# =============================================================================
# Output Formatting
# =============================================================================


def log_text_report(result: AuditResult) -> None:
    """Log human-readable report."""
    logger.info("=" * 70)
    logger.info("BioETL Structure Audit Report")
    logger.info("=" * 70)
    logger.info("")

    if result.must_violations:
        logger.info("## MUST Violations (%d) - BLOCKERS", len(result.must_violations))
        logger.info("")
        for v in result.must_violations:
            logger.info("  [%s] %s", v.category, v.path)
            logger.info("    → %s", v.message)
        logger.info("")

    if result.should_violations:
        logger.info(
            "## SHOULD Violations (%d) - RECOMMENDATIONS", len(result.should_violations)
        )
        logger.info("")
        for v in result.should_violations:
            logger.info("  [%s] %s", v.category, v.path)
            logger.info("    → %s", v.message)
        logger.info("")

    if not result.violations:
        logger.info("✓ Структура проекта соответствует File Policy")
        logger.info("")

    logger.info("=" * 70)
    logger.info(
        "Summary: %d MUST, %d SHOULD",
        len(result.must_violations),
        len(result.should_violations),
    )
    logger.info("=" * 70)


def log_json_report(result: AuditResult) -> None:
    """Log JSON report."""
    logger.info(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))


# =============================================================================
# CLI Entry Point
# =============================================================================


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="BioETL Structure Audit Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results in JSON format",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 on SHOULD violations too (default: only MUST)",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path.cwd(),
        help="Project root path (default: current directory)",
    )
    return parser.parse_args()


def main() -> int:
    """Entry point."""
    args = parse_args()

    # Resolve project root
    project_root = args.path.resolve()
    if not project_root.exists():
        logger.error("Error: Path does not exist: %s", project_root)
        return 2

    # Run audit
    result = run_audit(project_root)

    # Output results
    if args.json:
        log_json_report(result)
    else:
        log_text_report(result)

    # Determine exit code
    if result.must_violations:
        return 1
    if args.strict and result.should_violations:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
