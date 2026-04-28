#!/usr/bin/env python3
"""
cleanup_project.py - Clean up caches, build artifacts, and temporary files.

This tool removes generated and temporary files from the BioETL project,
including Python caches, build outputs, and log files.

Usage:
    # Dry-run (default) - show what would be deleted
    python src/tools/cleanup_project.py

    # Apply changes with log archiving
    python src/tools/cleanup_project.py --apply --archive-logs

    # Full cleanup including logs
    python src/tools/cleanup_project.py --apply --purge-logs

References:
    - 05-cleanup-policy.md §4.2: Cleanup procedures
    - RULES.md §7: Project maintenance

Aligned with RULES.md v5.24 (2026-01-06)
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from scripts.engineering.repo._root_governance import (
    is_within_blocked_cleanup_zone,
    load_root_governance_policy,
)

# Configure logging for CLI output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
DEFAULT_ARCHIVE_DIR = Path("reports/archived_logs/manual")


# =============================================================================
# Configuration: Directories and patterns to clean
# =============================================================================

# Python cache directories (always safe to delete)
PYTHON_CACHE_DIRS: tuple[str, ...] = (
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".hypothesis",
    ".benchmarks",
)

# Build artifacts
BUILD_DIRS: tuple[str, ...] = (
    "build",
    "dist",
    "htmlcov",
    "site",
    ".eggs",
)

# Egg-info patterns
EGGINFO_PATTERN = "*.egg-info"

# Coverage files
COVERAGE_FILES: tuple[str, ...] = (
    ".coverage",
    ".coverage.*",
    "coverage.xml",
)

# Python compiled files
COMPILED_PATTERNS: tuple[str, ...] = (
    "*.pyc",
    "*.pyo",
)

# Log file patterns
LOG_PATTERNS: tuple[str, ...] = (
    "*.log",
    "full_log.txt",
    "final_report*.txt",
    "project_rules_failures.txt",
)

# Temporary file patterns
TEMP_PATTERNS: tuple[str, ...] = (
    "*.tmp",
    "*.temp",
    "*.bak",
)


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class CleanupTarget:
    """A file or directory targeted for cleanup."""

    path: Path
    category: str
    size_bytes: int = 0
    is_dir: bool = False

    def to_dict(self) -> dict[str, str | int | bool]:
        """Convert to dictionary for reporting."""
        return {
            "path": str(self.path.relative_to(PROJECT_ROOT)),
            "category": self.category,
            "size_bytes": self.size_bytes,
            "is_dir": self.is_dir,
        }


@dataclass
class CleanupResult:
    """Result of cleanup operation."""

    targets: list[CleanupTarget] = field(default_factory=list)
    deleted: list[CleanupTarget] = field(default_factory=list)
    archived: list[CleanupTarget] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    dry_run: bool = True

    @property
    def total_size(self) -> int:
        """Total size of all targets in bytes."""
        return sum(t.size_bytes for t in self.targets)

    @property
    def deleted_size(self) -> int:
        """Total size of deleted items in bytes."""
        return sum(t.size_bytes for t in self.deleted)


# =============================================================================
# Cleanup Functions
# =============================================================================


def _get_dir_size(path: Path) -> int:
    """Calculate total size of a directory in bytes."""
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return total


def _is_venv_path(path: Path) -> bool:
    """Return True when the path is inside a virtual environment tree."""
    return ".venv" in path.parts or "venv" in path.parts


def _load_blocked_cleanup_paths(root: Path) -> frozenset[str]:
    """Best-effort loading of blocked cleanup zones for local artifact cleanup."""
    try:
        return load_root_governance_policy(root).blocked_cleanup_paths
    except RuntimeError:
        return frozenset()


def _is_excluded_cleanup_path(
    root: Path,
    path: Path,
    *,
    blocked_cleanup_paths: frozenset[str],
) -> bool:
    """Return True when a path must not be touched by local artifact cleanup."""
    if _is_venv_path(path):
        return True
    return is_within_blocked_cleanup_zone(path.relative_to(root), blocked_cleanup_paths)


def _safe_file_size(path: Path) -> int:
    """Return file size, tolerating transient filesystem errors."""
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _file_target(path: Path, category: str) -> CleanupTarget:
    """Build a CleanupTarget for a file."""
    return CleanupTarget(
        path=path,
        category=category,
        size_bytes=_safe_file_size(path),
        is_dir=False,
    )


def _dir_target(path: Path, category: str) -> CleanupTarget:
    """Build a CleanupTarget for a directory."""
    return CleanupTarget(
        path=path,
        category=category,
        size_bytes=_get_dir_size(path),
        is_dir=True,
    )


def _rglob_file_targets(
    root: Path,
    patterns: tuple[str, ...],
    category: str,
    *,
    excluded_parts: tuple[str, ...] = (),
    blocked_cleanup_paths: frozenset[str],
) -> list[CleanupTarget]:
    """Collect matching files under root while honoring path exclusions."""
    targets: list[CleanupTarget] = []
    excluded_parts_set = set(excluded_parts)
    for pattern in patterns:
        for matched_path in root.rglob(pattern):
            if (
                not matched_path.is_file()
                or _is_excluded_cleanup_path(
                    root,
                    matched_path,
                    blocked_cleanup_paths=blocked_cleanup_paths,
                )
            ):
                continue
            if excluded_parts_set.intersection(matched_path.parts):
                continue
            targets.append(_file_target(matched_path, category))
    return targets


def _find_cache_dirs(
    root: Path,
    *,
    blocked_cleanup_paths: frozenset[str],
) -> list[CleanupTarget]:
    """Find Python cache directories."""
    targets: list[CleanupTarget] = []
    for name in PYTHON_CACHE_DIRS:
        for cache_dir in root.rglob(name):
            if (
                not cache_dir.is_dir()
                or _is_excluded_cleanup_path(
                    root,
                    cache_dir,
                    blocked_cleanup_paths=blocked_cleanup_paths,
                )
            ):
                continue
            targets.append(_dir_target(cache_dir, "python_cache"))
    return targets


def _find_build_dirs(
    root: Path,
    *,
    blocked_cleanup_paths: frozenset[str],
) -> list[CleanupTarget]:
    """Find build artifact directories."""
    targets: list[CleanupTarget] = []
    for name in BUILD_DIRS:
        build_dir = root / name
        if (
            build_dir.exists()
            and build_dir.is_dir()
            and not _is_excluded_cleanup_path(
                root,
                build_dir,
                blocked_cleanup_paths=blocked_cleanup_paths,
            )
        ):
            targets.append(_dir_target(build_dir, "build_artifact"))

    # Egg-info directories
    for egg_dir in root.glob(EGGINFO_PATTERN):
        if (
            egg_dir.is_dir()
            and not _is_excluded_cleanup_path(
                root,
                egg_dir,
                blocked_cleanup_paths=blocked_cleanup_paths,
            )
        ):
            targets.append(_dir_target(egg_dir, "build_artifact"))

    return targets


def _find_coverage_files(
    root: Path,
    *,
    blocked_cleanup_paths: frozenset[str],
) -> list[CleanupTarget]:
    """Find coverage-related files."""
    targets: list[CleanupTarget] = []
    for pattern in COVERAGE_FILES:
        for cov_file in root.glob(pattern):
            if (
                cov_file.is_file()
                and not _is_excluded_cleanup_path(
                    root,
                    cov_file,
                    blocked_cleanup_paths=blocked_cleanup_paths,
                )
            ):
                targets.append(_file_target(cov_file, "coverage"))
    return targets


def _find_compiled_files(
    root: Path,
    *,
    blocked_cleanup_paths: frozenset[str],
) -> list[CleanupTarget]:
    """Find compiled Python files outside cache dirs."""
    return _rglob_file_targets(
        root,
        COMPILED_PATTERNS,
        "compiled",
        excluded_parts=("__pycache__",),
        blocked_cleanup_paths=blocked_cleanup_paths,
    )


def _find_log_files(
    root: Path,
    *,
    blocked_cleanup_paths: frozenset[str],
) -> list[CleanupTarget]:
    """Find log files."""
    return _rglob_file_targets(
        root,
        LOG_PATTERNS,
        "log",
        blocked_cleanup_paths=blocked_cleanup_paths,
    )


def _find_temp_files(
    root: Path,
    *,
    blocked_cleanup_paths: frozenset[str],
) -> list[CleanupTarget]:
    """Find temporary files."""
    return _rglob_file_targets(
        root,
        TEMP_PATTERNS,
        "temp",
        blocked_cleanup_paths=blocked_cleanup_paths,
    )


def _format_size(size_bytes: int) -> str:
    """Format size in human-readable form."""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def find_cleanup_targets(
    root: Path,
    include_logs: bool = False,
    blocked_cleanup_paths: frozenset[str] | None = None,
) -> list[CleanupTarget]:
    """Find all cleanup targets.

    Args:
        root: Project root directory.
        include_logs: If True, include log files in targets.

    Returns:
        List of CleanupTarget objects.
    """
    targets = []
    effective_blocked_paths = (
        _load_blocked_cleanup_paths(root)
        if blocked_cleanup_paths is None
        else blocked_cleanup_paths
    )

    # Always include these
    targets.extend(
        _find_cache_dirs(root, blocked_cleanup_paths=effective_blocked_paths)
    )
    targets.extend(
        _find_build_dirs(root, blocked_cleanup_paths=effective_blocked_paths)
    )
    targets.extend(
        _find_coverage_files(root, blocked_cleanup_paths=effective_blocked_paths)
    )
    targets.extend(
        _find_compiled_files(root, blocked_cleanup_paths=effective_blocked_paths)
    )
    targets.extend(
        _find_temp_files(root, blocked_cleanup_paths=effective_blocked_paths)
    )

    # Conditionally include logs
    if include_logs:
        targets.extend(
            _find_log_files(root, blocked_cleanup_paths=effective_blocked_paths)
        )

    return targets


def archive_logs(
    root: Path,
    targets: list[CleanupTarget],
    *,
    archive_dir: Path | None = None,
) -> list[CleanupTarget]:
    """Archive log files to reports/ directory.

    Args:
        root: Project root directory.
        targets: List of log targets to archive.

    Returns:
        List of archived targets.
    """
    archived: list[CleanupTarget] = []
    effective_archive_dir = (
        (root / archive_dir).resolve()
        if archive_dir is not None
        else (root / DEFAULT_ARCHIVE_DIR).resolve()
    )

    log_targets = [t for t in targets if t.category == "log"]
    if not log_targets:
        return archived

    effective_archive_dir.mkdir(parents=True, exist_ok=True)

    for target in log_targets:
        try:
            dest = effective_archive_dir / target.path.name
            shutil.copy2(target.path, dest)
            archived.append(target)
            logger.info("  Archived: %s -> %s", target.path.name, dest)
        except OSError as e:
            logger.warning("  Failed to archive %s: %s", target.path, e)

    return archived


def delete_targets(
    targets: list[CleanupTarget],
) -> tuple[list[CleanupTarget], list[str]]:
    """Delete cleanup targets.

    Args:
        targets: List of targets to delete.

    Returns:
        Tuple of (deleted targets, error messages).
    """
    deleted = []
    errors = []

    for target in targets:
        try:
            if target.is_dir:
                shutil.rmtree(target.path)
            else:
                target.path.unlink()
            deleted.append(target)
        except OSError as e:
            errors.append(f"Failed to delete {target.path}: {e}")

    return deleted, errors


# =============================================================================
# CLI Interface
# =============================================================================


def _targets_by_category(
    targets: list[CleanupTarget],
) -> dict[str, list[CleanupTarget]]:
    """Group targets by cleanup category."""
    by_category: dict[str, list[CleanupTarget]] = {}
    for target in targets:
        by_category.setdefault(target.category, []).append(target)
    return by_category


def _log_report_header(result: CleanupResult) -> None:
    """Emit report header and mode."""
    logger.info("=" * 70)
    logger.info("BioETL Project Cleanup Report")
    logger.info("=" * 70)
    logger.info("")
    logger.info(
        "MODE: %s",
        "Dry-run (no changes made)" if result.dry_run else "Apply (changes applied)",
    )
    logger.info("")


def _log_category_targets(category: str, targets: list[CleanupTarget]) -> None:
    """Emit all targets for one cleanup category."""
    cat_size = sum(t.size_bytes for t in targets)
    logger.info(
        "## %s (%d items, %s)",
        category.upper(),
        len(targets),
        _format_size(cat_size),
    )
    for target in targets:
        rel_path = target.path.relative_to(PROJECT_ROOT)
        marker = "[D]" if target.is_dir else "[F]"
        logger.info("  %s %s (%s)", marker, rel_path, _format_size(target.size_bytes))
    logger.info("")


def _log_archived_targets(archived: list[CleanupTarget]) -> None:
    """Emit archived log section."""
    if not archived:
        return
    logger.info("## ARCHIVED (%d items)", len(archived))
    for target in archived:
        logger.info("  %s", target.path.name)
    logger.info("")


def _log_errors(errors: list[str]) -> None:
    """Emit error section."""
    if not errors:
        return
    logger.info("## ERRORS (%d)", len(errors))
    for error in errors:
        logger.info("  %s", error)
    logger.info("")


def _log_report_summary(result: CleanupResult) -> None:
    """Emit final cleanup summary."""
    logger.info("=" * 70)
    logger.info(
        "Summary: %d targets (%s total)",
        len(result.targets),
        _format_size(result.total_size),
    )
    if not result.dry_run:
        logger.info(
            "Deleted: %d items (%s freed)",
            len(result.deleted),
            _format_size(result.deleted_size),
        )
    logger.info("=" * 70)


def log_report(result: CleanupResult) -> None:
    """Log cleanup report."""
    _log_report_header(result)
    for category, targets in sorted(_targets_by_category(result.targets).items()):
        _log_category_targets(category, targets)
    _log_archived_targets(result.archived)
    _log_errors(result.errors)
    _log_report_summary(result)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="BioETL Project Cleanup Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete files (default: dry-run)",
    )
    parser.add_argument(
        "--archive-logs",
        action="store_true",
        help="Archive log files to reports/ instead of deleting",
    )
    parser.add_argument(
        "--purge-logs",
        action="store_true",
        help="Include log files in cleanup (deletes them)",
    )
    parser.add_argument(
        "--archive-dir",
        type=Path,
        default=DEFAULT_ARCHIVE_DIR,
        help="Deterministic archive destination used with --archive-logs",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=PROJECT_ROOT,
        help="Project root path (default: auto-detected)",
    )
    return parser.parse_args()


def main() -> int:
    """Entry point."""
    args = parse_args()
    root = args.path.resolve()

    if not root.exists():
        logger.error("Error: Path does not exist: %s", root)
        return 2

    # Determine if logs should be included
    include_logs = args.purge_logs or args.archive_logs

    # Find targets
    targets = find_cleanup_targets(root, include_logs=include_logs)

    result = CleanupResult(
        targets=targets,
        dry_run=not args.apply,
    )

    if not targets:
        logger.info("No cleanup targets found.")
        return 0

    if args.apply:
        # Archive logs if requested
        if args.archive_logs:
            result.archived = archive_logs(
                root,
                targets,
                archive_dir=args.archive_dir,
            )
            # Remove archived logs from deletion targets
            archived_paths = {t.path for t in result.archived}
            targets = [t for t in targets if t.path not in archived_paths]

        # Delete remaining targets
        result.deleted, result.errors = delete_targets(targets)

    # Report results
    log_report(result)

    return 1 if result.errors else 0


if __name__ == "__main__":
    sys.exit(main())
