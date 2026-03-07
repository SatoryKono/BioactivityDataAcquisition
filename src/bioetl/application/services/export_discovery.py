"""Table discovery helpers for export service."""

from __future__ import annotations

from pathlib import Path

from bioetl.application.services.export_models import TableInfo


def _scan_layer_for_tables(base_path: Path, layer_name: str) -> list[TableInfo]:
    """Scan a layer directory for Delta tables."""
    tables: list[TableInfo] = []
    if not base_path.exists():
        return tables

    for provider_dir in base_path.iterdir():
        if not provider_dir.is_dir():
            continue
        tables.extend(_scan_provider_for_tables(provider_dir, layer_name))

    return tables


def _scan_provider_for_tables(provider_dir: Path, layer_name: str) -> list[TableInfo]:
    """Scan a provider directory for Delta tables."""
    tables: list[TableInfo] = []
    for entity_dir in provider_dir.iterdir():
        if not entity_dir.is_dir():
            continue
        for table_dir in entity_dir.iterdir():
            if table_dir.is_dir() and (table_dir / "_delta_log").exists():
                tables.append(
                    TableInfo(name=table_dir.name, layer=layer_name, path=table_dir)
                )
    return tables


__all__ = ["_scan_layer_for_tables", "_scan_provider_for_tables"]
