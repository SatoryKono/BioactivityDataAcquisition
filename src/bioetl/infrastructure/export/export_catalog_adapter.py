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
        base_path: str,
        layer: str,
    ) -> list[tuple[str, str]]:
        """Return discovered `(table_name, table_path)` pairs for one layer."""
        base_path_obj = Path(base_path)
        if not base_path_obj.exists():
            return []

        return [(name, str(path)) for name, path in _delta_tables(base_path_obj)]

    def resolve_table_path(
        self,
        *,
        base_path: str,
        table_name: str,
        layer: str,
    ) -> str:
        """Resolve one table path for the requested layer.

        A dotted table name is the Delta directory chain under the layer root.
        ``chembl.activity`` is ``<base>/chembl/activity``, not an extra nested
        directory whose name repeats the dotted identifier.
        """
        base_path_obj = Path(base_path)
        if not base_path_obj.exists():
            raise FileNotFoundError(f"Layer path not found: {base_path}")

        for name, table_dir in _delta_tables(base_path_obj):
            if name == table_name:
                return str(table_dir.resolve())

        raise FileNotFoundError(
            f"Table '{table_name}' not found in {layer} layer at {base_path}"
        )


def _delta_tables(base: Path) -> list[tuple[str, Path]]:
    """Name each Delta table by its path relative to the layer root."""
    found: list[tuple[str, Path]] = []
    for log in sorted(base.rglob("_delta_log")):
        if not log.is_dir():
            continue
        table = log.parent
        found.append((".".join(table.relative_to(base).parts), table))
    return found
