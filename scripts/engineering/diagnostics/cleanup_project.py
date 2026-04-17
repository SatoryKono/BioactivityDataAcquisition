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
from datetime import datetime
from pathlib import Path

# Configure logging for CLI output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


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


def _find_cache_dirs(root: Path) -> list[CleanupTarget]:
    """Find Python cache directories."""
    targets = []
    for name in PYTHON_CACHE_DIRS:
        for cache_dir in root.rglob(name):
            if cache_dir.is_dir():
                # Skip if in .venv
                if ".venv" in cache_dir.parts or "venv" in cache_dir.parts:
                    continue
                targets.append(
                    CleanupTarget(
                        path=cache_dir,
                        category="python_cache",
                        size_bytes=_get_dir_size(cache_dir),
                        is_dir=True,
                    )
                )
    return targets


def _find_build_dirs(root: Path) -> list[CleanupTarget]:
    """Find build artifact directories."""
    targets = []
    for name in BUILD_DIRS:
        build_dir = root / name
        if build_dir.exists() and build_dir.is_dir():
            targets.append(
                CleanupTarget(
                    path=build_dir,
                    category="build_artifact",
                    size_bytes=_get_dir_size(build_dir),
                    is_dir=True,
                )
            )

    # Egg-info directories
    for egg_dir in root.glob(EGGINFO_PATTERN):
        if egg_dir.is_dir():
            targets.append(
                CleanupTarget(
                    path=egg_dir,
                    category="build_artifact",
                    size_bytes=_get_dir_size(egg_dir),
                    is_dir=True,
                )
            )

    return targets


def _find_coverage_files(root: Path) -> list[CleanupTarget]:
    """Find coverage-related files."""
    targets = []
    for pattern in COVERAGE_FILES:
        for cov_file in root.glob(pattern):
            if cov_file.is_file():
                try:
                    size = cov_file.stat().st_size
                except OSError:
                    size = 0
                targets.append(
                    CleanupTarget(
                        path=cov_file,
                        category="coverage",
                        size_bytes=size,
                        is_dir=False,
                    )
                )
    return targets


def _find_compiled_files(root: Path) -> list[CleanupTarget]:
    """Find compiled Python files outside cache dirs."""
    targets = []
    for pattern in COMPILED_PATTERNS:
        for pyc_file in root.rglob(pattern):
            if pyc_file.is_file():
                # Skip if in .venv or __pycache__ (handled separately)
                if ".venv" in pyc_file.parts or "venv" in pyc_file.parts:
                    continue
                if "__pycache__" in pyc_file.parts:
                    continue
                try:
                    size = pyc_file.stat().st_size
                except OSError:
                    size = 0
                targets.append(
                    CleanupTarget(
                        path=pyc_file,
                        category="compiled",
                        size_bytes=size,
                        is_dir=False,
                    )
                )
    return targets


def _find_log_files(root: Path) -> list[CleanupTarget]:
    """Find log files."""
    targets = []
    for pattern in LOG_PATTERNS:
        for log_file in root.rglob(pattern):
            if log_file.is_file():
                # Skip if in .venv
                if ".venv" in log_file.parts or "venv" in log_file.parts:
                    continue
                try:
                    size = log_file.stat().st_size
                except OSError:
                    size = 0
                targets.append(
                    CleanupTarget(
                        path=log_file,
                        category="log",
                        size_bytes=size,
                        is_dir=False,
                    )
                )
    return targets


def _find_temp_files(root: Path) -> list[CleanupTarget]:
    """Find temporary files."""
    targets = []
    for pattern in TEMP_PATTERNS:
        for temp_file in root.rglob(pattern):
            if temp_file.is_file():
                # Skip if in .venv
                if ".venv" in temp_file.parts or "venv" in temp_file.parts:
                    continue
                try:
                    size = temp_file.stat().st_size
                except OSError:
                    size = 0
                targets.append(
                    CleanupTarget(
                        path=temp_file,
                        category="temp",
                        size_bytes=size,
                        is_dir=False,
                    )
                )
    return targets


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
) -> list[CleanupTarget]:
    """Find all cleanup targets.

    Args:
        root: Project root directory.
        include_logs: If True, include log files in targets.

    Returns:
        List of CleanupTarget objects.
    """
    targets = []

    # Always include these
    targets.extend(_find_cache_dirs(root))
    targets.extend(_find_build_dirs(root))
    targets.extend(_find_coverage_files(root))
    targets.extend(_find_compiled_files(root))
    targets.extend(_find_temp_files(root))

    # Conditionally include logs
    if include_logs:
        targets.extend(_find_log_files(root))

    return targets


def archive_logs(root: Path, targets: list[CleanupTarget]) -> list[CleanupTarget]:
    """Archive log files to reports/ directory.

    Args:
        root: Project root directory.
        targets: List of log targets to archive.

    Returns:
        List of archived targets.
    """
    archived: list[CleanupTarget] = []
    reports_dir = root / "reports" / "archived_logs"

    # Create archive directory with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_dir = reports_dir / timestamp

    log_targets = [t for t in targets if t.category == "log"]
    if not log_targets:
        return archived

    archive_dir.mkdir(parents=True, exist_ok=True)

    for target in log_targets:
        try:
            dest = archive_dir / target.path.name
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


def log_report(result: CleanupResult) -> None:
    """Log cleanup report."""
    logger.info("=" * 70)
    logger.info("BioETL Project Cleanup Report")
    logger.info("=" * 70)
    logger.info("")

    if result.dry_run:
        logger.info("MODE: Dry-run (no changes made)")
    else:
        logger.info("MODE: Apply (changes applied)")
    logger.info("")

    # Group targets by category
    by_category: dict[str, list[CleanupTarget]] = {}
    for target in result.targets:
        by_category.setdefault(target.category, []).append(target)

    for category, targets in sorted(by_category.items()):
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
            logger.info(
                "  %s %s (%s)", marker, rel_path, _format_size(target.size_bytes)
            )
        logger.info("")

    if result.archived:
        logger.info("## ARCHIVED (%d items)", len(result.archived))
        for target in result.archived:
            logger.info("  %s", target.path.name)
        logger.info("")

    if result.errors:
        logger.info("## ERRORS (%d)", len(result.errors))
        for error in result.errors:
            logger.info("  %s", error)
        logger.info("")

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
            result.archived = archive_logs(root, targets)
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
