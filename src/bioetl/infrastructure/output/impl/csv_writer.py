import hashlib
import os
import time
from pathlib import Path
import pandas as pd

from bioetl.infrastructure.output.contracts import WriterABC, WriteResult


class CsvWriterImpl(WriterABC):
    """
    Запись CSV.
    """

    @property
    def atomic(self) -> bool:
        return True

    def write(self, df: pd.DataFrame, path: Path) -> WriteResult:
        start_time = time.monotonic()

        tmp_path = path.with_suffix(".tmp")

        df.to_csv(tmp_path, index=False, encoding="utf-8")
        os.replace(tmp_path, path)

        checksum = self._compute_checksum(path)

        duration = time.monotonic() - start_time

        return WriteResult(
            path=path,
            row_count=len(df),
            checksum=checksum,
            duration_sec=duration,
        )

    def supports_format(self, fmt: str) -> bool:
        return fmt.lower() == "csv"

    def _compute_checksum(self, path: Path) -> str:
        sha256 = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

