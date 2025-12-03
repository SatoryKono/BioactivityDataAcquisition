"""CSV-backed record source implementation."""
from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import pandas as pd

from bioetl.clients.records.contracts import RecordSourceABC
from bioetl.domain.records import RawRecord


class CsvRecordSourceImpl(RecordSourceABC):
    """Read full records from a CSV file and stream as dictionaries."""

    def __init__(self, path: str, *, limit: int | None = None) -> None:
        self._path = path
        self._limit = limit

    @staticmethod
    def peek_columns(path: str) -> list[str]:
        """Read header columns without materializing the dataset."""
        header = pd.read_csv(path, nrows=0)
        return list(header.columns)

    def iter_records(self) -> Iterator[RawRecord]:
        df = pd.read_csv(self._path)
        if self._limit:
            df = df.head(self._limit)
        yield from df.to_dict(orient="records")

    def metadata(self) -> dict[str, Any]:
        return {
            "source": "csv",
            "path": self._path,
            "limit": self._limit,
        }


__all__ = ["CsvRecordSourceImpl"]
