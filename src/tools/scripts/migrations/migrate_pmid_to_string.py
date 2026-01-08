#!/usr/bin/env python
"""Migration script: Convert pubmed_id from int to string in Delta Lake tables.

This script migrates existing ChEMBL Document and Document Similarity tables
from int64 pubmed_id to string pubmed_id for cross-provider consistency.

BREAKING CHANGE: This migration is required after updating to the new schema
where PMID is stored as a numeric string instead of int64.

Usage:
    python scripts/migrations/migrate_pmid_to_string.py --data-dir ./data

Options:
    --data-dir PATH     Path to data directory (default: ./data)
    --dry-run           Show what would be changed without modifying data
    --backup            Create backup before migration (recommended)

Requirements:
    - deltalake >= 0.10.0
    - polars >= 0.19.0
"""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def migrate_table(
    table_path: Path,
    pmid_columns: list[str],
    dry_run: bool = False,
) -> dict[str, int]:
    """Migrate pubmed_id columns from int to string in a Delta table.

    Args:
        table_path: Path to the Delta table.
        pmid_columns: List of column names to migrate (e.g., ["pubmed_id"]).
        dry_run: If True, show what would be changed without modifying.

    Returns:
        Dictionary with migration statistics.
    """
    try:
        import polars as pl
        from deltalake import DeltaTable
    except ImportError as e:
        logger.error(f"Required package not installed: {e}")
        logger.error("Install with: pip install deltalake polars")
        sys.exit(1)

    if not table_path.exists():
        logger.warning(f"Table not found: {table_path}")
        return {"skipped": 1, "migrated": 0, "rows": 0}

    try:
        dt = DeltaTable(str(table_path))
    except Exception as e:
        logger.warning(f"Could not open Delta table {table_path}: {e}")
        return {"skipped": 1, "migrated": 0, "rows": 0}

    # Read current data
    df = pl.read_delta(str(table_path))
    original_rows = len(df)

    logger.info(f"Processing {table_path} ({original_rows} rows)")

    # Check which columns need migration
    columns_to_migrate = []
    for col in pmid_columns:
        if col not in df.columns:
            logger.info(f"  Column {col} not found, skipping")
            continue

        dtype = df.schema[col]
        if dtype == pl.Utf8 or dtype == pl.String:
            logger.info(f"  Column {col} already string, skipping")
            continue

        if dtype in (pl.Int64, pl.Int32, pl.Float64):
            columns_to_migrate.append(col)
            logger.info(f"  Column {col} ({dtype}) will be migrated to string")

    if not columns_to_migrate:
        logger.info(f"  No columns need migration in {table_path}")
        return {"skipped": 0, "migrated": 0, "rows": original_rows}

    if dry_run:
        logger.info(f"  [DRY RUN] Would migrate columns: {columns_to_migrate}")
        return {
            "skipped": 0,
            "migrated": len(columns_to_migrate),
            "rows": original_rows,
        }

    # Perform migration
    for col in columns_to_migrate:
        # Convert int/float to string, handling nulls
        df = df.with_columns(
            pl.when(pl.col(col).is_null())
            .then(None)
            .otherwise(pl.col(col).cast(pl.Int64).cast(pl.Utf8))
            .alias(col)
        )
        logger.info(f"  Converted {col} to string")

    # Write back to Delta table (overwrite)
    df.write_delta(
        str(table_path),
        mode="overwrite",
        overwrite_schema=True,
    )

    logger.info(f"  Migration complete for {table_path}")
    return {"skipped": 0, "migrated": len(columns_to_migrate), "rows": original_rows}


def backup_table(table_path: Path, backup_dir: Path) -> Path | None:
    """Create a backup of a Delta table.

    Args:
        table_path: Path to the Delta table.
        backup_dir: Directory to store backups.

    Returns:
        Path to the backup, or None if table doesn't exist.
    """
    if not table_path.exists():
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = backup_dir / f"{table_path.name}_backup_{timestamp}"

    logger.info(f"Creating backup: {table_path} -> {backup_path}")
    shutil.copytree(table_path, backup_path)

    return backup_path


def main() -> int:
    """Run the PMID migration."""
    parser = argparse.ArgumentParser(
        description="Migrate pubmed_id from int to string in Delta Lake tables"
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("./data"),
        help="Path to data directory (default: ./data)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without modifying data",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create backup before migration (recommended)",
    )

    args = parser.parse_args()

    data_dir = args.data_dir.resolve()
    silver_dir = data_dir / "silver"

    if not silver_dir.exists():
        logger.error(f"Silver directory not found: {silver_dir}")
        return 1

    logger.info(f"Starting PMID migration (dry_run={args.dry_run})")
    logger.info(f"Data directory: {data_dir}")

    # Tables and their PMID columns to migrate
    tables_to_migrate = {
        "chembl_document": ["pubmed_id"],
        "chembl_document_similarity": ["pubmed_id1", "pubmed_id2"],
    }

    # Create backups if requested
    if args.backup and not args.dry_run:
        backup_dir = data_dir / "backups"
        backup_dir.mkdir(exist_ok=True)
        logger.info(f"Backup directory: {backup_dir}")

        for table_name in tables_to_migrate:
            table_path = silver_dir / table_name
            backup_table(table_path, backup_dir)

    # Migrate tables
    total_stats = {"skipped": 0, "migrated": 0, "rows": 0}

    for table_name, pmid_columns in tables_to_migrate.items():
        table_path = silver_dir / table_name
        stats = migrate_table(table_path, pmid_columns, dry_run=args.dry_run)

        total_stats["skipped"] += stats["skipped"]
        total_stats["migrated"] += stats["migrated"]
        total_stats["rows"] += stats["rows"]

    # Summary
    logger.info("=" * 60)
    logger.info("Migration Summary")
    logger.info(f"  Tables skipped: {total_stats['skipped']}")
    logger.info(f"  Columns migrated: {total_stats['migrated']}")
    logger.info(f"  Total rows processed: {total_stats['rows']}")

    if args.dry_run:
        logger.info("  [DRY RUN] No changes were made")

    return 0


if __name__ == "__main__":
    sys.exit(main())
