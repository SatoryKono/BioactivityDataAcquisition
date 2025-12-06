import time
from pathlib import Path
import pandas as pd

from bioetl.infrastructure.output.column_order import apply_column_order
from bioetl.infrastructure.output.contracts import WriterABC, WriteResult


class ParquetWriterImpl(WriterABC):
    """
    Запись Parquet.
    """

    @property
    def atomic(self) -> bool:
        return True

    def write(
        self,
        df: pd.DataFrame,
        path: Path,
        *,
        column_order: list[str] | None = None,
    ) -> WriteResult:
        start_time = time.monotonic()

        df_to_write = apply_column_order(df, column_order)

        df_to_write.to_parquet(path, index=False)
        
        duration = time.monotonic() - start_time
        
        return WriteResult(
            path=path,
            row_count=len(df_to_write),
            checksum="",
            duration_sec=duration,
        )

    def supports_format(self, fmt: str) -> bool:
        return fmt.lower() == "parquet"

