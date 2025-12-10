"""Parquet writer implementation with atomic writes."""

from __future__ import annotations

import warnings
from collections.abc import Callable
from pathlib import Path

import pandas as pd

from bioetl.infrastructure.output.impl.base_writer import BaseWriter


class ParquetWriter(BaseWriter):
    """
    Запись Parquet.
    """

    def __init__(self, *, checksum_fn: Callable[[Path], str] | None = None) -> None:
        super().__init__(atomic=True, checksum_fn=checksum_fn)

    def _write_frame(self, df: pd.DataFrame, path: Path) -> None:
        df.to_parquet(path, index=False)

    def has_format_support(self, fmt: str) -> bool:
        """Return True if parquet format is requested."""
        return fmt.lower() == "parquet"


# Deprecated aliases for backward compatibility
_DEPRECATED_ALIASES = {
    "ParquetWriterImpl": "ParquetWriter",
}


def __getattr__(name: str):
    if name in _DEPRECATED_ALIASES:
        warnings.warn(
            f"{name} is deprecated, use {_DEPRECATED_ALIASES[name]} instead. "
            "Will be removed in v3.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        return globals()[_DEPRECATED_ALIASES[name]]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["ParquetWriter", "ParquetWriterImpl"]
