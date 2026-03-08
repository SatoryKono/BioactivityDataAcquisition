#!/usr/bin/env python3
"""Migration script to rename ChEMBL molecule structure field names.

This script renames the following fields in the chembl_molecule Delta Lake table:
- structure_canonical_smiles -> canonical_smiles
- structure_standard_inchi -> standard_inchi
- structure_standard_inchi_key -> inchi_key

This is a BREAKING CHANGE migration. Ensure all downstream consumers are updated
before running this script.

Usage:
    python scripts/migrations/rename_structure_fields.py --data-dir ./data
    python scripts/migrations/rename_structure_fields.py --data-dir ./data --dry-run
    python scripts/migrations/rename_structure_fields.py --data-dir ./data --layer silver
    python scripts/migrations/rename_structure_fields.py --data-dir ./data --layer gold

Requirements:
    - deltalake >= 0.15.0
    - pyarrow >= 14.0.0
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from deltalake import DeltaTable

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Field rename mapping: old_name -> new_name
FIELD_RENAMES: dict[str, str] = {
    "structure_canonical_smiles": "canonical_smiles",
    "structure_standard_inchi": "standard_inchi",
    "structure_standard_inchi_key": "inchi_key",
}


def get_table_path(data_dir: Path, layer: str) -> Path:
    """Get the path to the chembl_molecule Delta table for the specified layer.

    Args:
        data_dir: Base data directory.
        layer: Data layer ('silver' or 'gold').

    Returns:
        Path to the Delta table.

    """
    return data_dir / layer / "chembl_molecule"


def check_table_exists(table_path: Path) -> bool:
    """Check if a Delta table exists at the given path.

    Args:
        table_path: Path to check.

    Returns:
        True if table exists, False otherwise.

    """
    delta_log = table_path / "_delta_log"
    return delta_log.exists() and delta_log.is_dir()


def get_current_schema(dt: DeltaTable) -> list[str]:
    """Get current column names from a Delta table.

    Args:
        dt: DeltaTable instance.

    Returns:
        List of column names.

    """
    return [field.name for field in dt.schema().to_pyarrow()]


def migrate_table(
    table_path: Path,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Migrate a single Delta table by renaming structure fields.

    Args:
        table_path: Path to the Delta table.
        dry_run: If True, only report what would be changed.

    Returns:
        Tuple of (fields_renamed, fields_skipped).

    """
    from deltalake import DeltaTable

    if not check_table_exists(table_path):
        logger.warning(f"Table not found at {table_path}, skipping")
        return 0, 0

    dt = DeltaTable(str(table_path))
    current_columns = set(get_current_schema(dt))

    fields_renamed = 0
    fields_skipped = 0

    for old_name, new_name in FIELD_RENAMES.items():
        if old_name not in current_columns:
            logger.info(f"  Column '{old_name}' not found (may already be renamed)")
            fields_skipped += 1
            continue

        if new_name in current_columns:
            logger.warning(
                f"  Target column '{new_name}' already exists, skipping '{old_name}'"
            )
            fields_skipped += 1
            continue

        if dry_run:
            logger.info(f"  [DRY-RUN] Would rename: {old_name} -> {new_name}")
        else:
            logger.info(f"  Renaming: {old_name} -> {new_name}")
            # Delta Lake ALTER TABLE RENAME COLUMN
            # Note: This requires delta-rs with ALTER COLUMN support
            try:
                dt.alter.rename_column(old_name, new_name)
                logger.info(f"    Successfully renamed {old_name} -> {new_name}")
            except Exception as e:
                logger.error(f"    Failed to rename {old_name}: {e}")
                raise

        fields_renamed += 1

    return fields_renamed, fields_skipped


def migrate_chembl_molecule_tables(
    data_dir: Path,
    layers: list[str],
    dry_run: bool = False,
) -> dict[str, tuple[int, int]]:
    """Migrate chembl_molecule tables across specified layers.

    Args:
        data_dir: Base data directory.
        layers: List of layers to migrate ('silver', 'gold', or both).
        dry_run: If True, only report what would be changed.

    Returns:
        Dictionary mapping layer name to (renamed, skipped) counts.

    """
    results: dict[str, tuple[int, int]] = {}

    for layer in layers:
        table_path = get_table_path(data_dir, layer)
        logger.info(f"Processing {layer} layer: {table_path}")

        renamed, skipped = migrate_table(table_path, dry_run=dry_run)
        results[layer] = (renamed, skipped)

        logger.info(f"  {layer}: {renamed} fields renamed, {skipped} fields skipped")

    return results


def create_backward_compat_view_sql(layer: str) -> str:
    """Generate SQL for creating backward-compatible view.

    Args:
        layer: Data layer name.

    Returns:
        SQL statement for creating the compatibility view.

    """
    return f"""
-- Backward compatibility view for {layer}.chembl_molecule
-- This view provides the old field names as aliases
CREATE OR REPLACE VIEW {layer}.chembl_molecule_compat AS
SELECT
    *,
    canonical_smiles AS structure_canonical_smiles,
    standard_inchi AS structure_standard_inchi,
    inchi_key AS structure_standard_inchi_key
FROM {layer}.chembl_molecule;
"""


def main() -> int:
    """Main entry point for the migration script.

    Returns:
        Exit code (0 for success, non-zero for failure).

    """
    parser = argparse.ArgumentParser(
        description="Migrate ChEMBL molecule structure field names",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Base data directory containing silver/gold tables",
    )
    parser.add_argument(
        "--layer",
        choices=["silver", "gold", "all"],
        default="all",
        help="Layer(s) to migrate (default: all)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be changed without making changes",
    )
    parser.add_argument(
        "--show-compat-sql",
        action="store_true",
        help="Print SQL for creating backward-compatible views",
    )

    args = parser.parse_args()

    if not args.data_dir.exists():
        logger.error(f"Data directory not found: {args.data_dir}")
        return 1

    layers = ["silver", "gold"] if args.layer == "all" else [args.layer]

    if args.dry_run:
        logger.info("=== DRY RUN MODE - No changes will be made ===")

    logger.info(f"Data directory: {args.data_dir}")
    logger.info(f"Layers to migrate: {layers}")
    logger.info(f"Field renames: {FIELD_RENAMES}")

    try:
        results = migrate_chembl_molecule_tables(
            args.data_dir,
            layers,
            dry_run=args.dry_run,
        )

        # Summary
        logger.info("=== Migration Summary ===")
        total_renamed = 0
        total_skipped = 0
        for layer, (renamed, skipped) in results.items():
            logger.info(f"  {layer}: {renamed} renamed, {skipped} skipped")
            total_renamed += renamed
            total_skipped += skipped

        logger.info(f"  Total: {total_renamed} renamed, {total_skipped} skipped")

        if args.show_compat_sql:
            logger.info("\n=== Backward Compatibility SQL ===")
            for layer in layers:
                print(create_backward_compat_view_sql(layer))

        if args.dry_run:
            logger.info("=== DRY RUN COMPLETE - No changes were made ===")

        return 0

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
