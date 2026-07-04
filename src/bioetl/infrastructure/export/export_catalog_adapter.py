"""Filesystem-backed export catalog adapter."""

from __future__ import annotations

from pathlib import Path

from bioetl.domain.ports import ExportCatalogPort

__all__ = ["ExportCatalogAdapter"]


class ExportCatalogAdapter(ExportCatalogPort):
    """Discover Delta tables and resolve table paths from the filesystem."""

    def list_tables(
        self,
        *,
        base_path: Path,
        layer: str,
    ) -> list[tuple[str, Path]]:
        """Return discovered `(table_name, table_path)` pairs for one layer."""
        if not base_path.exists():
            return []

        tables: list[tuple[str, Path]] = []
        for provider_dir in base_path.iterdir():
            if not provider_dir.is_dir():
                continue
            tables.extend(
                self._list_provider_tables(provider_dir=provider_dir, layer=layer)
            )
        return tables

    def resolve_table_path(
        self,
        *,
        base_path: Path,
        table_name: str,
        layer: str,
    ) -> Path:
        """Resolve one table path for the requested layer."""
        if not base_path.exists():
            raise FileNotFoundError(f"Layer path not found: {base_path}")

        for provider_dir in base_path.iterdir():
            if not provider_dir.is_dir():
                continue
            for entity_dir in provider_dir.iterdir():
                if not entity_dir.is_dir():
                    continue
                table_dir = entity_dir / table_name
                if table_dir.exists() and (table_dir / "_delta_log").exists():
                    return table_dir.resolve()

        raise FileNotFoundError(
            f"Table '{table_name}' not found in {layer} layer at {base_path}"
        )

    def _list_provider_tables(
        self,
        *,
        provider_dir: Path,
        layer: str,
    ) -> list[tuple[str, Path]]:
        tables: list[tuple[str, Path]] = []
        for entity_dir in provider_dir.iterdir():
            if not entity_dir.is_dir():
                continue
            for table_dir in entity_dir.iterdir():
                if table_dir.is_dir() and (table_dir / "_delta_log").exists():
                    tables.append((table_dir.name, table_dir))
        return tables
