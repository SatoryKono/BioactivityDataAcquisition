"""Ports for export table discovery and file writing."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal, Protocol, runtime_checkable

from bioetl.domain.types import DebugExportPack, DebugExportResult

__all__ = [
    "DebugExportPort",
    "ExportCatalogPort",
    "ExportFileFingerprint",
    "ExportJobStatus",
    "ExportRedactionProfile",
    "ExportRole",
    "ExportWriterPort",
]

ExportFormatLiteral = Literal["csv", "xlsx", "tsv"]


class ExportJobStatus(StrEnum):
    """Governed export job lifecycle states for projections and audit trails."""

    REQUESTED = "requested"
    AUTHORIZED = "authorized"
    MATERIALIZED = "materialized"
    EXPIRED = "expired"
    REVOKED = "revoked"
    FAILED = "failed"


class ExportRole(StrEnum):
    """Bounded export access roles used by application services and interfaces."""

    VIEWER = "viewer"
    INVESTIGATOR = "investigator"
    EXPORTER = "exporter"
    ADMIN = "admin"


class ExportRedactionProfile(StrEnum):
    """Stable redaction profiles for governed exports."""

    DEFAULT = "default"
    NONE = "none"


def _validate_export_fingerprint_size(size_bytes: int) -> None:
    if size_bytes < 0:
        raise ValueError(f"size_bytes must be non-negative, got {size_bytes!r}")


def _normalize_export_sha256(sha256: str) -> str:
    digest = sha256.strip().lower()
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise ValueError(
            f"sha256 must be a 64-character lowercase hex digest, got {sha256!r}"
        )
    return digest


@dataclass(frozen=True, slots=True)
class ExportFileFingerprint:
    """Stable fingerprint for an exported file artifact."""

    path: str
    size_bytes: int
    sha256: str

    def __post_init__(self) -> None:
        _validate_export_fingerprint_size(self.size_bytes)
        digest = _normalize_export_sha256(self.sha256)
        if digest != self.sha256:
            object.__setattr__(self, "sha256", digest)


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


@runtime_checkable
class DebugExportPort(Protocol):
    """Persist deterministic debug-export audit packs."""

    def write_pack(self, *, pack: DebugExportPack) -> DebugExportResult:
        """Persist the provided audit pack and return artifact metadata."""
        ...

