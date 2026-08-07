"""BronzeWriteResult value object for Bronze layer write operation results.

Implements RULES.md §2.1.1 - Bronze Layer specifications.

This value object encapsulates the result of a Bronze write operation,
providing all necessary information for downstream lineage tracking
in Silver and Gold layers.

Requirements:
- REQ-LINEAGE-001: Track Bronze paths for Silver lineage
- REQ-DATA-004: Atomic writes verification via checksum
"""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.types import BatchID

__all__ = [
    "BronzeWriteResult",
]


def _clean_path_segments(normalized: str) -> list[str]:
    parts: list[str] = []
    for part in normalized.split("/"):
        if part in {"", "."}:
            continue
        parts.append(part)
    return parts


def _normalized_path_parts(relative_path: str) -> list[str]:
    """Return cleaned path segments without empty/dot/parent parts."""
    normalized = relative_path.replace("\\", "/").strip("/")
    if not normalized:
        raise ValueError("relative_path must include provider/entity segments")
    parts = _clean_path_segments(normalized)
    if ".." in parts:
        raise ValueError("relative_path must not contain parent-directory segments")
    return parts


def _strip_v1_prefix(parts: list[str]) -> list[str]:
    if not parts:
        return parts
    if parts[0] != "v1":
        return parts
    return parts[1:]


def _has_provider_entity(parts: list[str]) -> bool:
    if len(parts) < 2:
        return False
    if not parts[0].strip():
        return False
    return bool(parts[1].strip())


def _parse_provider_entity(relative_path: str) -> tuple[str, str]:
    """Parse provider and entity from a Bronze relative path."""
    parts = _strip_v1_prefix(_normalized_path_parts(relative_path))
    if not _has_provider_entity(parts):
        raise ValueError("relative_path must include provider/entity segments")
    return parts[0], parts[1]


@dataclass(frozen=True, slots=True)
class BronzeWriteResult:
    """Result of a Bronze layer write operation.

    This frozen dataclass captures all metadata from a Bronze write operation
    needed for lineage tracking in downstream Medallion layers.

    Attributes:
        batch_id: Unique identifier for the written batch.
        relative_path: Path relative to Bronze root (for storage references).
        absolute_path: Full filesystem path (for lineage tracking).
        record_count: Number of records written in this batch.
        compressed_size: Size of compressed file in bytes.
        uncompressed_size: Size of uncompressed data in bytes.
        checksum_blake2: BLAKE2b checksum of compressed file for integrity verification.

    Example:
        >>> from uuid import UUID
        >>> result = BronzeWriteResult(
        ...     batch_id=BatchID(UUID("00000000-0000-0000-0000-000000000201")),
        ...     relative_path="chembl/activity/2024-01-15/batch_abc.jsonl.zst",
        ...     absolute_path="/data/output/bronze/chembl/activity/2024-01-15/batch_abc.jsonl.zst",
        ...     record_count=1000,
        ...     compressed_size=50000,
        ...     uncompressed_size=200000,
        ...     checksum_blake2="abc123...",
        ... )
        >>> result.relative_path
        'chembl/activity/2024-01-15/batch_abc.jsonl.zst'
    """

    batch_id: BatchID
    relative_path: str
    absolute_path: str
    record_count: int
    compressed_size: int
    uncompressed_size: int
    checksum_blake2: str

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        self._validate_non_negative_fields()
        self._validate_required_strings()

    def _validate_non_negative_fields(self) -> None:
        """Validate that numeric fields are non-negative."""
        if self.record_count < 0:
            raise ValueError(
                f"record_count must be non-negative, got {self.record_count}"
            )
        if self.compressed_size < 0:
            raise ValueError(
                f"compressed_size must be non-negative, got {self.compressed_size}"
            )
        if self.uncompressed_size < 0:
            raise ValueError(
                f"uncompressed_size must be non-negative, got {self.uncompressed_size}"
            )

    def _validate_required_strings(self) -> None:
        """Validate that required string fields are not empty."""
        if not self.relative_path:
            raise ValueError("relative_path cannot be empty")
        if not self.absolute_path:
            raise ValueError("absolute_path cannot be empty")
        if not self.checksum_blake2:
            raise ValueError("checksum_blake2 cannot be empty")
        # Fail closed on relative paths that lack provider/entity segments.
        _parse_provider_entity(self.relative_path)

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio (uncompressed / compressed).

        Returns:
            Compression ratio, or 1.0 when either size is zero so callers never
            hit ZeroDivisionError on empty or pre-compression artifacts.
        """
        if self.uncompressed_size == 0:
            return 1.0
        if self.compressed_size == 0:
            return 1.0
        return self.uncompressed_size / self.compressed_size

    @property
    def table_name(self) -> str:
        """Compatibility table name derived from relative path.

        Returns:
            Table name in ``provider.entity`` format.
        """
        provider, entity = self.provider_entity
        return f"{provider}.{entity}"

    @property
    def provider_entity(self) -> tuple[str, str]:
        """Extract provider/entity from Bronze relative path."""
        return _parse_provider_entity(self.relative_path)
