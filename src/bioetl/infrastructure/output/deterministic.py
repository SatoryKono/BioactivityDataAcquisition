"""Deterministic Parquet writer with atomic operations.

This module provides a concrete implementation of DeterministicWriterABC
using Parquet format. It ensures reproducible outputs through:
- Deterministic row ordering (sorting)
- Atomic writes (temp file + rename)
- Checksum verification
"""

from __future__ import annotations

import hashlib
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING, Callable

from bioetl.domain.output.deterministic import (
    DeterministicWriterABC,
    DeterministicWriteResult,
)

if TYPE_CHECKING:
    import pandas as pd

    from bioetl.domain.data import TabularData


class _BaseDeterministicWriter(DeterministicWriterABC):
    """Base class for deterministic writers with shared functionality.

    This abstract base class extracts common code shared between
    different format writers (Parquet, CSV, etc.).
    """

    def _prepare_dataframe(self, data: "TabularData") -> "pd.DataFrame":
        """Convert TabularData to DataFrame."""
        import pandas as pd

        if hasattr(data, "underlying"):
            return data.underlying  # PandasTabularAdapter
        elif hasattr(data, "to_records"):
            return pd.DataFrame(data.to_records())
        else:
            return data  # type: ignore[return-value]

    def _sort_dataframe(
        self,
        df: "pd.DataFrame",
        sort_columns: tuple[str, ...] | None,
        reset_index: bool,
    ) -> "pd.DataFrame":
        """Sort DataFrame for determinism."""
        if sort_columns:
            return df.sort_values(list(sort_columns)).reset_index(drop=True)
        elif reset_index:
            return df.reset_index(drop=True)
        return df

    def _write_atomic_impl(
        self,
        df: "pd.DataFrame",
        target_path: Path,
        write_fn: Callable[[Path], None],
    ) -> DeterministicWriteResult:
        """Core atomic write implementation.

        Args:
            df: DataFrame to write.
            target_path: Final destination path.
            write_fn: Function that writes df to the given path.

        Returns:
            Write result with checksum and metadata.
        """
        # 1. Ensure parent directory exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # 2. Write to temporary file
        with tempfile.NamedTemporaryFile(
            dir=target_path.parent,
            suffix=".tmp",
            delete=False,
        ) as tmp:
            temp_path = Path(tmp.name)

        try:
            write_fn(temp_path)

            # 3. Compute checksum
            checksum = self.compute_checksum(temp_path)
            bytes_written = temp_path.stat().st_size

            # 4. Atomic rename
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


class DeterministicParquetWriter(_BaseDeterministicWriter):
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
        df = self._prepare_dataframe(data)
        df = self._sort_dataframe(df, sort_columns, reset_index)
        return self._write_atomic_impl(
            df, target_path, lambda p: df.to_parquet(p, index=False)
        )


class DeterministicCSVWriter(_BaseDeterministicWriter):
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
        df = self._prepare_dataframe(data)
        df = self._sort_dataframe(df, sort_columns, reset_index)
        return self._write_atomic_impl(
            df, target_path, lambda p: df.to_csv(p, index=False)
        )


__all__ = [
    "DeterministicCSVWriter",
    "DeterministicParquetWriter",
]
