from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pandas as pd

from bioetl.infrastructure.output.impl.base_writer import BaseWriterImpl


class ParquetWriterImpl(BaseWriterImpl):
    """
    Запись Parquet.
    """

    def __init__(self, *, checksum_fn: Callable[[Path], str] | None = None) -> None:
        super().__init__(atomic=True, checksum_fn=checksum_fn)

    def _write_frame(self, df: pd.DataFrame, path: Path) -> None:
        df.to_parquet(path, index=False)

    def supports_format(self, fmt: str) -> bool:
        return fmt.lower() == "parquet"
