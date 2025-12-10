"""
CSV Writer implementation.
"""

from __future__ import annotations

import warnings
from pathlib import Path

import pandas as pd

from bioetl.infrastructure.files.checksum import compute_file_sha256
from bioetl.infrastructure.output.impl.base_writer import BaseWriter


class CsvWriter(BaseWriter):
    """
    Запись CSV.
    Делегирует атомарность и хеширование внешнему фасаду.
    """

    def __init__(self) -> None:
        super().__init__(atomic=False, checksum_fn=compute_file_sha256)

    def _write_frame(self, df: pd.DataFrame, path: Path) -> None:
        df.to_csv(path, index=False, encoding="utf-8")

    def has_format_support(self, fmt: str) -> bool:
        """Return True if writer can handle the requested format."""
        return fmt.lower() == "csv"


# Deprecated aliases for backward compatibility
_DEPRECATED_ALIASES = {
    "CsvWriterImpl": "CsvWriter",
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


__all__ = ["CsvWriter", "CsvWriterImpl"]
