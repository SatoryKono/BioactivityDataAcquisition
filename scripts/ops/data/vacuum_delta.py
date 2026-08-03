#!/usr/bin/env python3
"""
vacuum_delta.py - VACUUM operation for Delta Lake tables.

Performs weekly VACUUM maintenance on Delta Lake Silver tables to remove
old transaction log files and data files no longer referenced by the
current table version.

Usage:
    # VACUUM all Silver tables with default retention (7 days)
    python src/tools/vacuum_delta.py

    # VACUUM specific table
    python src/tools/vacuum_delta.py --table silver/chembl/activity

    # Custom retention period
    python src/tools/vacuum_delta.py --retention-days 14

    # Dry-run to see what would be vacuumed
    python src/tools/vacuum_delta.py --dry-run

References:
    - RULES.md §2.1.1: VACUUM MUST run weekly
    - 05-cleanup-policy.md §4.3: Delta Lake maintenance
    - ADR-014: Deterministic writes

Make target: make vacuum-silver

Aligned with RULES.md v5.24 (2026-01-06)
"""

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass, field
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

# Default data directory
DEFAULT_DATA_DIR = PROJECT_ROOT / "data"

# Default retention period in days
DEFAULT_RETENTION_DAYS = 7


# =============================================================================
# Data Models
# =============================================================================


@dataclass
class VacuumResult:
    """Result of VACUUM operation on a single table."""

    table_path: Path
    table_name: str
    success: bool
    files_removed: int = 0
    bytes_freed: int = 0
    error: str | None = None
    dry_run: bool = False


@dataclass
class VacuumReport:
    """Overall VACUUM report."""

    results: list[VacuumResult] = field(default_factory=list)
    retention_hours: int = 168  # 7 days default

    @property
    def total_tables(self) -> int:
        """Total number of tables processed."""
        return len(self.results)

    @property
    def successful(self) -> int:
        """Number of successful VACUUM operations."""
        return sum(1 for r in self.results if r.success)

    @property
    def failed(self) -> int:
        """Number of failed VACUUM operations."""
        return sum(1 for r in self.results if not r.success)

    @property
    def total_files_removed(self) -> int:
        """Total files removed across all tables."""
        return sum(r.files_removed for r in self.results)

    @property
    def total_bytes_freed(self) -> int:
        """Total bytes freed across all tables."""
        return sum(r.bytes_freed for r in self.results)


# =============================================================================
# Delta Lake VACUUM Functions
# =============================================================================


def _is_delta_table(path: Path) -> bool:
    """Check if path is a Delta Lake table."""
    delta_log = path / "_delta_log"
    return delta_log.exists() and delta_log.is_dir()


def _find_delta_tables(base_path: Path) -> list[Path]:
    """Find all Delta Lake tables under base path.

    Args:
        base_path: Directory to search for Delta tables.

    Returns:
        List of paths to Delta Lake tables.
    """
    tables: list[Path] = []

    if not base_path.exists():
        return tables

    # Check if base_path itself is a Delta table
    if _is_delta_table(base_path):
        tables.append(base_path)
        return tables

    # Recursively search for Delta tables
    for item in base_path.iterdir():
        if item.is_dir():
            if _is_delta_table(item):
                tables.append(item)
            else:
                # Search subdirectories
                tables.extend(_find_delta_tables(item))

    return tables


def _get_table_name(table_path: Path, base_path: Path) -> str:
    """Get human-readable table name from path.

    Args:
        table_path: Path to the Delta table.
        base_path: Base data directory.

    Returns:
        Table name like 'silver/chembl/activity'.
    """
    try:
        rel_path = table_path.relative_to(base_path)
        return str(rel_path).replace("\\", "/")
    except ValueError:
        return str(table_path)


def vacuum_table(
    table_path: Path,
    table_name: str,
    retention_hours: int,
    dry_run: bool = False,
) -> VacuumResult:
    """Perform VACUUM on a single Delta table.

    Args:
        table_path: Path to the Delta Lake table.
        table_name: Human-readable table name.
        retention_hours: File retention period in hours.
        dry_run: If True, only report what would be done.

    Returns:
        VacuumResult with operation details.
    """
    try:
        from deltalake import DeltaTable

        dt = DeltaTable(str(table_path))

        if dry_run:
            # In dry-run mode, we can't actually count files
            # but we can verify the table is accessible
            logger.info("  [DRY-RUN] Would VACUUM: %s", table_name)
            return VacuumResult(
                table_path=table_path,
                table_name=table_name,
                success=True,
                dry_run=True,
            )

        # Perform VACUUM with retention period
        # Note: Delta Lake VACUUM returns list of deleted file URIs
        files_deleted = dt.vacuum(
            retention_hours=retention_hours,
            enforce_retention_duration=False,  # Allow shorter retention
            dry_run=False,
        )

        # Count removed files
        files_removed = len(files_deleted) if files_deleted else 0

        logger.info(
            "  VACUUM completed: %s (%d files removed)", table_name, files_removed
        )

        return VacuumResult(
            table_path=table_path,
            table_name=table_name,
            success=True,
            files_removed=files_removed,
        )

    except ImportError:
        return VacuumResult(
            table_path=table_path,
            table_name=table_name,
            success=False,
            error="deltalake package not installed",
        )
    except Exception as e:
        error_msg = str(e)
        logger.warning("  VACUUM failed: %s - %s", table_name, error_msg)
        return VacuumResult(
            table_path=table_path,
            table_name=table_name,
            success=False,
            error=error_msg,
        )


def vacuum_all_tables(
    data_dir: Path,
    layer: str = "silver",
    retention_days: int = DEFAULT_RETENTION_DAYS,
    dry_run: bool = False,
) -> VacuumReport:
    """VACUUM all Delta tables in specified layer.

    Args:
        data_dir: Base data directory.
        layer: Data layer to process (silver, gold).
        retention_days: File retention period in days.
        dry_run: If True, only report what would be done.

    Returns:
        VacuumReport with all operation results.
    """
    retention_hours = retention_days * 24
    report = VacuumReport(retention_hours=retention_hours)

    layer_path = data_dir / layer
    if not layer_path.exists():
        logger.warning("Layer directory does not exist: %s", layer_path)
        return report

    tables = _find_delta_tables(layer_path)
    logger.info("Found %d Delta tables in %s", len(tables), layer_path)

    for table_path in sorted(tables):
        table_name = _get_table_name(table_path, data_dir)
        result = vacuum_table(
            table_path=table_path,
            table_name=table_name,
            retention_hours=retention_hours,
            dry_run=dry_run,
        )
        report.results.append(result)

    return report


def vacuum_single_table(
    table_path: Path,
    data_dir: Path,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    dry_run: bool = False,
) -> VacuumReport:
    """VACUUM a specific Delta table.

    Args:
        table_path: Path to the Delta table.
        data_dir: Base data directory (for naming).
        retention_days: File retention period in days.
        dry_run: If True, only report what would be done.

    Returns:
        VacuumReport with operation result.
    """
    retention_hours = retention_days * 24
    report = VacuumReport(retention_hours=retention_hours)

    if not _is_delta_table(table_path):
        logger.error("Not a Delta table: %s", table_path)
        report.results.append(
            VacuumResult(
                table_path=table_path,
                table_name=str(table_path),
                success=False,
                error="Not a Delta Lake table",
            )
        )
        return report

    table_name = _get_table_name(table_path, data_dir)
    result = vacuum_table(
        table_path=table_path,
        table_name=table_name,
        retention_hours=retention_hours,
        dry_run=dry_run,
    )
    report.results.append(result)

    return report


# =============================================================================
# CLI Interface
# =============================================================================


def _format_size(size_bytes: int) -> str:
    """Format size in human-readable form."""
    size = float(size_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def log_report(report: VacuumReport) -> None:
    """Log VACUUM report."""
    logger.info("")
    logger.info("=" * 70)
    logger.info("Delta Lake VACUUM Report")
    logger.info("=" * 70)
    logger.info("")

    retention_days = report.retention_hours // 24
    logger.info(
        "Retention Period: %d days (%d hours)", retention_days, report.retention_hours
    )
    logger.info("")

    if not report.results:
        logger.info("No tables processed.")
        return

    # Successful operations
    successful = [r for r in report.results if r.success]
    if successful:
        logger.info("## SUCCESSFUL (%d tables)", len(successful))
        for result in successful:
            if result.dry_run:
                logger.info("  [DRY-RUN] %s", result.table_name)
            else:
                logger.info(
                    "  %s: %d files removed", result.table_name, result.files_removed
                )
        logger.info("")

    # Failed operations
    failed = [r for r in report.results if not r.success]
    if failed:
        logger.info("## FAILED (%d tables)", len(failed))
        for result in failed:
            logger.info("  %s: %s", result.table_name, result.error)
        logger.info("")

    logger.info("=" * 70)
    logger.info(
        "Summary: %d tables processed, %d successful, %d failed",
        report.total_tables,
        report.successful,
        report.failed,
    )
    if not any(r.dry_run for r in report.results):
        logger.info("Total files removed: %d", report.total_files_removed)
    logger.info("=" * 70)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Delta Lake VACUUM Tool for BioETL",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--table",
        type=Path,
        help="Path to specific table (default: all Silver tables)",
    )
    parser.add_argument(
        "--layer",
        type=str,
        default="silver",
        choices=["silver", "gold"],
        help="Data layer to VACUUM (default: silver)",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=DEFAULT_RETENTION_DAYS,
        help=f"File retention period in days (default: {DEFAULT_RETENTION_DAYS})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only show what would be done",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DEFAULT_DATA_DIR,
        help=f"Data directory (default: {DEFAULT_DATA_DIR})",
    )
    return parser.parse_args()


def main() -> int:
    """Entry point."""
    args = parse_args()

    logger.info("Delta Lake VACUUM Tool")
    logger.info("")

    if args.dry_run:
        logger.info("Mode: DRY-RUN (no changes will be made)")
    else:
        logger.info("Mode: APPLY (will remove old files)")
    logger.info("Retention: %d days", args.retention_days)
    logger.info("")

    if args.table:
        # VACUUM specific table
        table_path = args.table
        if not table_path.is_absolute():
            table_path = args.data_dir / table_path
        report = vacuum_single_table(
            table_path=table_path,
            data_dir=args.data_dir,
            retention_days=args.retention_days,
            dry_run=args.dry_run,
        )
    else:
        # VACUUM all tables in layer
        report = vacuum_all_tables(
            data_dir=args.data_dir,
            layer=args.layer,
            retention_days=args.retention_days,
            dry_run=args.dry_run,
        )

    log_report(report)

    return 1 if report.failed > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
