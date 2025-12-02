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
        
        df.to_csv(path, index=False, encoding="utf-8")
        
        duration = time.monotonic() - start_time
        
        # Checksum calculation is done by UnifiedOutputWriter wrapper
        return WriteResult(
            path=path,
            row_count=len(df),
            checksum="", 
            duration_sec=duration,
        )

    def supports_format(self, fmt: str) -> bool:
        return fmt.lower() == "csv"

