#!/usr/bin/env python3
"""Delta Table Integrity Checker.

Validates the integrity of Delta Lake tables by checking version,
file count, and read operations. Useful for diagnosing Delta table issues.

Usage:
    python scripts/ops/data/check_delta_integrity.py <table_path>

Arguments:
    table_path: Path to the Delta table (default: data/output/silver/chembl/molecule)

Examples:
    # Check default table
    python scripts/ops/data/check_delta_integrity.py

    # Check specific table
    python scripts/ops/data/check_delta_integrity.py data/output/silver/pubchem/molecule

Returns:
    int: Exit code (0 for success, non-zero for integrity errors)

Raises:
    ValueError: When table path is invalid
    RuntimeError: When Delta table cannot be read
"""

import sys

import polars as pl
from deltalake import DeltaTable


def main(table_path: str | None = None) -> int:
    """Check Delta table integrity.

    Args:
        table_path: Path to the Delta table (optional, uses default if not provided)

    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    if table_path is None:
        table_path = "data/output/silver/chembl/molecule"

    try:
        print(f"Loading table: {table_path}")
        dt = DeltaTable(table_path)
        print(f"Table version: {dt.version()}")
        print(f"Table files: {len(dt.files())}")

        # Try reading it with polars
        df = pl.read_delta(table_path)
        print(f"Polars read successful: {df.shape}")
        return 0
    except Exception as e:
        print(f"ERROR: {e}")
        return 1


if __name__ == "__main__":
    table_path = sys.argv[1] if len(sys.argv) > 1 else None
    sys.exit(main(table_path))
