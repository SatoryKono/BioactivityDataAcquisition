"""Contracts for deterministic file writing.

This module defines abstract interfaces for deterministic and atomic
file writing operations. Deterministic writes ensure that identical
input data produces byte-for-byte identical output files, which is
critical for reproducibility and caching.

Key guarantees:
1. **Determinism**: Same input always produces identical output bytes
2. **Atomicity**: Writes either complete fully or not at all
3. **Verifiability**: Output includes checksum for validation
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from bioetl.domain.data import TabularData


@dataclass(frozen=True)
class WriteResult:
    """Result of deterministic write operation.

    Contains information about the write operation including
    the output path, checksum, and statistics.

    Attributes:
        path: Path where data was written.
        checksum: SHA-256 checksum of written file.
        row_count: Number of rows written.
        is_atomic: Whether write was atomic (temp + rename).
        bytes_written: Total bytes written to file.
    """

    path: Path
    checksum: str
    row_count: int
    is_atomic: bool
    bytes_written: int = 0

    def verify(self, expected_checksum: str) -> bool:
        """Verify checksum matches expected value.

        Args:
            expected_checksum: Expected checksum to compare.

        Returns:
            True if checksums match.
        """
        return self.checksum == expected_checksum


class DeterministicWriterABC(ABC):
    """Contract for deterministic file writing.

    Implementations must guarantee:
    1. Output is byte-for-byte identical for same input data
    2. Write is atomic (temp file + rename pattern)
    3. Checksum is computed and returned

    The determinism requirement means:
    - Row order must be deterministic (sorted)
    - Column order must be deterministic
    - Index must be reset or deterministic
    - No timestamp or random values in output

    Example:
        >>> writer: DeterministicWriterABC = ...
        >>> result1 = writer.write_atomic(data, path1, sort_columns=("id",))
        >>> result2 = writer.write_atomic(data, path2, sort_columns=("id",))
        >>> assert result1.checksum == result2.checksum  # Always true
    """

    @abstractmethod
    def write_atomic(
        self,
        data: TabularData,
        target_path: Path,
        *,
        sort_columns: tuple[str, ...] | None = None,
        reset_index: bool = True,
    ) -> WriteResult:
        """Write data atomically with deterministic output.

        The write operation follows these steps:
        1. Sort data by sort_columns (for determinism)
        2. Reset index if requested
        3. Write to temporary file
        4. Compute checksum
        5. Atomic rename to target path

        Args:
            data: Tabular data to write.
            target_path: Final destination path.
            sort_columns: Columns to sort by for determinism.
                If None, data is written in current order.
            reset_index: Whether to reset the index before writing.

        Returns:
            WriteResult with path, checksum, and statistics.

        Raises:
            IOError: If write operation fails.
            PermissionError: If target path is not writable.
        """
        ...

    @abstractmethod
    def verify_checksum(self, path: Path, expected: str) -> bool:
        """Verify file checksum matches expected value.

        Args:
            path: Path to file to verify.
            expected: Expected checksum (SHA-256 hex digest).

        Returns:
            True if checksum matches.

        Raises:
            FileNotFoundError: If file does not exist.
        """
        ...

    @abstractmethod
    def compute_checksum(self, path: Path) -> str:
        """Compute checksum of file.

        Args:
            path: Path to file.

        Returns:
            SHA-256 hex digest of file contents.

        Raises:
            FileNotFoundError: If file does not exist.
        """
        ...


__all__ = [
    "DeterministicWriterABC",
    "WriteResult",
]
