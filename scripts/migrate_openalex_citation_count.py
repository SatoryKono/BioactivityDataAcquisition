#!/usr/bin/env python3
"""Migration script: Rename cited_by_count to citation_count in OpenAlex tables.

This script renames the `cited_by_count` column to `citation_count` in OpenAlex
Silver and Gold Delta Lake tables to align with the unified citation count
naming convention used by CrossRef and SemanticScholar providers.

BREAKING CHANGE: This migration modifies the schema of existing Delta Lake tables.

Usage:
    python scripts/migrate_openalex_citation_count.py --data-dir /path/to/data

    # Dry-run mode (default, shows what would be done):
    python scripts/migrate_openalex_citation_count.py --data-dir /path/to/data --dry-run

    # Execute the migration:
    python scripts/migrate_openalex_citation_count.py --data-dir /path/to/data --execute

Requirements:
    - deltalake>=0.14.0
    - polars>=0.20.0

See also:
    - RULES.md §2.4 (Schema Standards)
    - OpenAlex API documentation: https://docs.openalex.org/api-entities/works
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import polars as pl
    from deltalake import DeltaTable, write_deltalake
except ImportError as e:
    print(f"Error: Required dependencies not installed: {e}")
    print("Install with: pip install deltalake polars")
    sys.exit(1)


def migrate_table(table_path: Path, dry_run: bool = True) -> bool:
    """Migrate a single Delta Lake table.

    Args:
        table_path: Path to the Delta Lake table.
        dry_run: If True, only show what would be done without making changes.

    Returns:
        True if migration was successful or skipped (no changes needed).
        False if an error occurred.
    """
    if not table_path.exists():
        print(f"  Table not found: {table_path}")
        return True  # Not an error, table just doesn't exist yet

    try:
        dt = DeltaTable(str(table_path))
        schema = dt.schema()
        column_names = [field.name for field in schema.fields]

        # Check if migration is needed
        if "cited_by_count" not in column_names:
            if "citation_count" in column_names:
                print(f"  Already migrated: {table_path}")
                return True
            print(f"  No citation count column found: {table_path}")
            return True

        print(f"  Found cited_by_count column in: {table_path}")

        if dry_run:
            print("  [DRY-RUN] Would rename cited_by_count -> citation_count")
            return True

        # Read the table
        df = pl.read_delta(str(table_path))

        # Rename the column
        df = df.rename({"cited_by_count": "citation_count"})

        # Write back with overwrite mode
        write_deltalake(
            str(table_path),
            df.to_arrow(),
            mode="overwrite",
            overwrite_schema=True,
        )

        print(f"  Successfully migrated: {table_path}")
        return True

    except Exception as e:
        print(f"  Error migrating {table_path}: {e}")
        return False


def main() -> int:
    """Run the migration script.

    Returns:
        Exit code: 0 for success, 1 for failure.
    """
    parser = argparse.ArgumentParser(
        description="Migrate OpenAlex cited_by_count to citation_count",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Path to the data directory containing Silver/Gold tables",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Show what would be done without making changes (default)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually execute the migration (disables dry-run)",
    )
    args = parser.parse_args()

    dry_run = not args.execute

    print("=" * 60)
    print("OpenAlex Citation Count Migration")
    print("=" * 60)
    print(f"Data directory: {args.data_dir}")
    print(f"Mode: {'DRY-RUN' if dry_run else 'EXECUTE'}")
    print()

    if dry_run:
        print("NOTE: This is a dry-run. Use --execute to apply changes.")
        print()

    # Define table paths to migrate
    tables_to_migrate = [
        args.data_dir / "silver" / "openalex_publication",
        args.data_dir / "gold" / "openalex_publication",
    ]

    success = True
    for table_path in tables_to_migrate:
        print(f"\nProcessing: {table_path}")
        if not migrate_table(table_path, dry_run):
            success = False

    print()
    print("=" * 60)
    if dry_run:
        print("Dry-run complete. Use --execute to apply changes.")
    elif success:
        print("Migration completed successfully.")
    else:
        print("Migration completed with errors.")
    print("=" * 60)

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
