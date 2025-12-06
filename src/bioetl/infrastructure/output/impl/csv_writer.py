"""
CSV Writer implementation.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from bioetl.infrastructure.files.checksum import compute_file_sha256
from bioetl.infrastructure.output.impl.base_writer import BaseWriterImpl


class CsvWriterImpl(BaseWriterImpl):
    """
    Запись CSV.
    Делегирует атомарность и хеширование внешнему фасаду.
    """

    def __init__(self) -> None:
        super().__init__(atomic=False, checksum_fn=compute_file_sha256)

    def _write_frame(self, df: pd.DataFrame, path: Path) -> None:
        df.to_csv(path, index=False, encoding="utf-8")

    def supports_format(self, fmt: str) -> bool:
        return fmt.lower() == "csv"
