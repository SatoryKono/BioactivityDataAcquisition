"""Deterministic Parquet writer with atomic operations.

This module provides a concrete implementation of DeterministicWriterABC
using Parquet format. It ensures reproducible outputs through:
- Deterministic row ordering (sorting)
- Atomic writes (temp file + rename)
- Checksum verification
"""

from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.output.deterministic import (
    DeterministicWriterABC,
    DeterministicWriteResult,
)

if TYPE_CHECKING:
    from bioetl.domain.data import TabularData


class DeterministicParquetWriter(DeterministicWriterABC):
    """Deterministic Parquet writer with atomic operations.

    Writes Parquet files with guaranteed determinism and atomicity.
    Uses temporary file + atomic rename pattern to ensure writes
    either complete fully or not at all.

    Example:
        >>> writer = DeterministicParquetWriter()
        >>> result = writer.write_atomic(
        ...     data=df,
        ...     target_path=Path("output.parquet"),
        ...     sort_columns=("id",),
        ... )
        >>> print(f"Written {result.row_count} rows, checksum: {result.checksum}")
    """

    def write_atomic(
        self,
        data: "TabularData",
        target_path: Path,
        *,
        sort_columns: tuple[str, ...] | None = None,
        reset_index: bool = True,
    ) -> DeterministicWriteResult:
        """Write data atomically with deterministic output."""
        import pandas as pd

        # Get underlying DataFrame or convert
        if hasattr(data, "underlying"):
            df = data.underlying  # PandasTabularAdapter
        elif hasattr(data, "to_records"):
            df = pd.DataFrame(data.to_records())
        else:
            # Assume it's already a DataFrame
            df = data  # type: ignore[assignment]

        # 1. Sort for determinism
        if sort_columns:
            df = df.sort_values(list(sort_columns)).reset_index(drop=True)
        elif reset_index:
            df = df.reset_index(drop=True)

        # 2. Ensure parent directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 3. Write to temporary file
        with tempfile.NamedTemporaryFile(
            dir=target_path.parent,
            suffix=".tmp",
            delete=False,
        ) as tmp:
            temp_path = Path(tmp.name)

        try:
            df.to_parquet(temp_path, index=False)

            # 4. Compute checksum
            checksum = self.compute_checksum(temp_path)
            bytes_written = temp_path.stat().st_size

            # 5. Atomic rename
            temp_path.rename(target_path)

            return DeterministicWriteResult(
                path=target_path,
                checksum=checksum,
                row_count=len(df),
                is_atomic=True,
                bytes_written=bytes_written,
            )
        except Exception:
            # Clean up temp file on failure
            if temp_path.exists():
                temp_path.unlink()
            raise

    def verify_checksum(self, path: Path, expected: str) -> bool:
        """Verify file checksum matches expected value."""
        actual = self.compute_checksum(path)
        return actual == expected

    def compute_checksum(self, path: Path) -> str:
        """Compute SHA-256 checksum of file."""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()


class DeterministicCSVWriter(DeterministicWriterABC):
    """Deterministic CSV writer with atomic operations.

    Similar to DeterministicParquetWriter but outputs CSV format.
    Useful for debugging and human-readable outputs.
    """

    def write_atomic(
        self,
        data: "TabularData",
        target_path: Path,
        *,
        sort_columns: tuple[str, ...] | None = None,
        reset_index: bool = True,
    ) -> DeterministicWriteResult:
        """Write data atomically with deterministic output."""
        import pandas as pd

        # Get underlying DataFrame or convert
        if hasattr(data, "underlying"):
            df = data.underlying
        elif hasattr(data, "to_records"):
            df = pd.DataFrame(data.to_records())
        else:
            df = data  # type: ignore[assignment]

        # 1. Sort for determinism
        if sort_columns:
            df = df.sort_values(list(sort_columns)).reset_index(drop=True)
        elif reset_index:
            df = df.reset_index(drop=True)

        # 2. Ensure parent directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 3. Write to temporary file
        with tempfile.NamedTemporaryFile(
            dir=target_path.parent,
            suffix=".tmp",
            delete=False,
            mode="w",
        ) as tmp:
            temp_path = Path(tmp.name)

        try:
            df.to_csv(temp_path, index=False)

            # 4. Compute checksum
            checksum = self.compute_checksum(temp_path)
            bytes_written = temp_path.stat().st_size

            # 5. Atomic rename
            temp_path.rename(target_path)

            return DeterministicWriteResult(
                path=target_path,
                checksum=checksum,
                row_count=len(df),
                is_atomic=True,
                bytes_written=bytes_written,
            )
        except Exception:
            if temp_path.exists():
                temp_path.unlink()
            raise

    def verify_checksum(self, path: Path, expected: str) -> bool:
        """Verify file checksum matches expected value."""
        actual = self.compute_checksum(path)
        return actual == expected

    def compute_checksum(self, path: Path) -> str:
        """Compute SHA-256 checksum of file."""
        hasher = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
        return hasher.hexdigest()


__all__ = [
    "DeterministicCSVWriter",
    "DeterministicParquetWriter",
]
