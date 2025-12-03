"""
CSV Writer implementation.
"""
import hashlib
import time
from pathlib import Path
import pandas as pd

from bioetl.infrastructure.output.contracts import WriterABC, WriteResult


class CsvWriterImpl(WriterABC):
    """
    Запись CSV.
    Делегирует атомарность и хеширование внешнему фасаду.
    """

    @property
    def atomic(self) -> bool:
        return False

    def write(self, df: pd.DataFrame, path: Path) -> WriteResult:
        start_time = time.monotonic()

        df.to_csv(path, index=False, encoding="utf-8")

        duration = time.monotonic() - start_time

        # Calculate checksum
        sha256 = hashlib.sha256()
        sha256.update(path.read_bytes())
        checksum = sha256.hexdigest()

        return WriteResult(
            path=path,
            row_count=len(df),
            duration_sec=duration,
            checksum=checksum
        )

    def supports_format(self, fmt: str) -> bool:
        return fmt.lower() == "csv"
