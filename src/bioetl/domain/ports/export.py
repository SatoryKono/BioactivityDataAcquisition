"""Ports for export table discovery and file writing."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

__all__ = ["ExportCatalogPort", "ExportFileFingerprint", "ExportWriterPort"]

ExportFormatLiteral = Literal["csv", "xlsx", "tsv"]


@dataclass(frozen=True, slots=True)
class ExportFileFingerprint:
    """Stable fingerprint for an exported file artifact."""

    path: str
    size_bytes: int
    sha256: str


@runtime_checkable
class ExportCatalogPort(Protocol):
    """Locate Delta tables for export workflows."""

    def list_tables(
        self,
        *,
        base_path: str,
        layer: str,
    ) -> list[tuple[str, str]]:
        """Return discovered `(table_name, table_path)` pairs for one layer."""
        ...

    def resolve_table_path(
        self,
        *,
        base_path: str,
        table_name: str,
        layer: str,
    ) -> str:
        """Resolve one table path or raise when it does not exist."""
        ...


@runtime_checkable
class ExportWriterPort(Protocol):
    """Persist exported tables to external file formats."""

    def write_export(
        self,
        *,
        table: object,
        table_name: str,
        layer: str,
        fmt: ExportFormatLiteral,
        output_dir: str,
    ) -> str:
        """Write one exported table and return the created file path."""
        ...

    def write_manifest(
        self,
        *,
        manifest_name: str,
        payload: dict[str, object],
        output_dir: str,
    ) -> str:
        """Write one deterministic JSON export manifest and return its path."""
        ...

    def fingerprint_file(self, *, path: str) -> ExportFileFingerprint:
        """Return deterministic size/checksum metadata for one export artifact."""
        ...
