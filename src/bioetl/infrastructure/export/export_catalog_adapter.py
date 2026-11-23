"""Filesystem-backed export catalog adapter."""

from __future__ import annotations

from pathlib import Path

from bioetl.domain.ports import ExportCatalogPort
from bioetl.infrastructure.storage.delta.table_ops import resolve_delta_table_path

__all__ = ["ExportCatalogAdapter"]


def _is_delta_table(path: Path) -> bool:
    """Return whether ``path`` is a Delta table directory."""
    return path.is_dir() and (path / "_delta_log").is_dir()


def _discover_delta_tables(base_path: Path) -> list[tuple[str, Path]]:
    """Return Delta tables stored directly at their contract path.

    ``resolve_delta_table_path`` maps ``chembl.target`` to ``chembl/target``.
    The directory that contains ``_delta_log`` is the table. An extra child
    named after the dotted table is not part of the contract, and directories
    inside a table are not separate tables.
    """
    discovered: list[tuple[str, Path]] = []
    for directory, dirnames, _filenames in base_path.walk(top_down=True):
        dirnames[:] = sorted(name for name in dirnames if name != "_delta_log")
        if directory == base_path or not _is_delta_table(directory):
            continue
        relative = directory.relative_to(base_path)
        discovered.append((".".join(relative.parts), directory))
        dirnames[:] = []
    discovered.sort(key=lambda item: item[0])
    return discovered


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
        if not base_path_obj.is_dir():
            return []
        return [
            (name, str(path.resolve()))
            for name, path in _discover_delta_tables(base_path_obj)
        ]

    def resolve_table_path(
        self,
        *,
        base_path: str,
        table_name: str,
        layer: str,
    ) -> str:
        """Resolve one table path for the requested layer."""
        base_path_obj = Path(base_path)
        if not base_path_obj.is_dir():
            raise FileNotFoundError(f"Layer path not found: {base_path}")
        candidate = Path(
            resolve_delta_table_path(
                base_path=str(base_path_obj),
                table_name=table_name,
                flat_structure=False,
            )
        )
        if _is_delta_table(candidate):
            return str(candidate.resolve())
        raise FileNotFoundError(
            f"Table '{table_name}' not found in {layer} layer at {base_path}"
        )
