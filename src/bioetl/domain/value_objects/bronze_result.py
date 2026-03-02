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
from pathlib import Path

from bioetl.domain.types import BatchID


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
        >>> result = BronzeWriteResult(
        ...     batch_id=BatchID(uuid4()),
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

    def exists(self) -> bool:
        """Check if the written Bronze file exists on disk.

        Returns:
            True if condition is met, False otherwise.
        """
        return Path(self.absolute_path).exists()

    @property
    def compression_ratio(self) -> float:
        """Calculate compression ratio (uncompressed / compressed).

        Returns:
            Compression ratio, or 1.0 if uncompressed_size is 0.
        """
        if self.uncompressed_size == 0:
            return 1.0
        return self.uncompressed_size / self.compressed_size
