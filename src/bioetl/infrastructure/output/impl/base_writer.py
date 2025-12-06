"""
Base helpers for writer implementations.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from bioetl.infrastructure.output.column_order import apply_column_order
from bioetl.infrastructure.output.contracts import WriterABC, WriteResult


class BaseWriterImpl(WriterABC):
    """Template for concrete writers with shared bookkeeping."""

    def __init__(
        self,
        *,
        atomic: bool,
        checksum_fn: Callable[[Path], str] | None = None,
    ) -> None:
        self._atomic = atomic
        self._checksum_fn = checksum_fn

    @property
    def atomic(self) -> bool:
        return self._atomic

    def write(
        self,
        df: pd.DataFrame,
        path: Path,
        *,
        column_order: list[str] | None = None,
    ) -> WriteResult:
        start_time = time.monotonic()

        df_to_write = apply_column_order(df, column_order)
        self._write_frame(df_to_write, path)

        duration = time.monotonic() - start_time
        checksum = self._compute_checksum(path)

        return WriteResult(
            path=path,
            row_count=len(df_to_write),
            duration_sec=duration,
            checksum=checksum,
        )

    def _compute_checksum(self, path: Path) -> str | None:
        if self._checksum_fn is None:
            return None
        return self._checksum_fn(path)

    def _write_frame(self, df: pd.DataFrame, path: Path) -> None:
        raise NotImplementedError
