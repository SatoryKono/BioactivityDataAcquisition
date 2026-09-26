"""Gold Delta vacuum execution owned by infrastructure (#11241)."""

from __future__ import annotations

from pathlib import Path


def vacuum_gold_delta_table(
    table_path: Path,
    *,
    retention_hours: int,
    dry_run: bool,
) -> list[str]:
    """Vacuum one Gold Delta table directory and return removed file paths."""
    from deltalake import DeltaTable

    table = DeltaTable(str(table_path))
    removed = table.vacuum(retention_hours=retention_hours, dry_run=dry_run)
    return list(removed or [])
