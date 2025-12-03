"""CSV-based record source implementations."""
from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import pandas as pd

from bioetl.domain.record_source import RawRecord, RecordSource
from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.infrastructure.config.models import ChemblSourceConfig, CsvInputOptions
from bioetl.infrastructure.logging.contracts import LoggerAdapterABC


def _chunk_list(data: list[Any], size: int) -> Iterator[list[Any]]:
    for i in range(0, len(data), size):
        yield data[i : i + size]


class CsvRecordSource(RecordSource):
    """Record source that reads full datasets from CSV."""

    def __init__(
        self,
        input_path: Path,
        csv_options: dict[str, Any] | CsvInputOptions,
        limit: int | None,
        logger: LoggerAdapterABC,
    ) -> None:
        self._input_path = input_path
        self._csv_options = self._ensure_csv_options(csv_options)
        self._limit = limit
        self._logger = logger

    def iter_records(self) -> Iterable[RawRecord]:
        header = 0 if self._csv_options.header else None
        self._logger.info(
            f"Extracting records from CSV dataset: {self._input_path}"
        )
        df = pd.read_csv(
            self._input_path,
            delimiter=self._csv_options.delimiter,
            header=header,
        )
        if self._limit is not None:
            df = df.head(self._limit)
        return df.to_dict(orient="records")

    @staticmethod
    def _ensure_csv_options(
        options: dict[str, Any] | CsvInputOptions,
    ) -> CsvInputOptions:
        if isinstance(options, CsvInputOptions):
            return options
        return CsvInputOptions(**options)


class IdListRecordSource(RecordSource):
    """Record source for ID-only CSVs enriched via API."""

    def __init__(
        self,
        input_path: Path,
        id_column: str,
        csv_options: dict[str, Any] | CsvInputOptions,
        limit: int | None,
        extraction_service: ExtractionServiceABC,
        source_config: ChemblSourceConfig,
        entity: str,
        filter_key: str,
        logger: LoggerAdapterABC,
    ) -> None:
        if not id_column:
            raise ValueError("ID column must be provided for ID-only mode")
        if not filter_key:
            raise ValueError("Filter key must be provided for ID-only mode")

        self._input_path = input_path
        self._id_column = id_column
        self._csv_options = self._ensure_csv_options(csv_options)
        self._limit = limit
        self._extraction_service = extraction_service
        self._source_config = source_config
        self._entity = entity
        self._filter_key = filter_key
        self._logger = logger

    def iter_records(self) -> Iterable[RawRecord]:
        header = 0 if self._csv_options.header else None
        usecols = [self._id_column] if self._csv_options.header else [0]
        names = [self._id_column] if not self._csv_options.header else None

        df_ids = pd.read_csv(
            self._input_path,
            delimiter=self._csv_options.delimiter,
            usecols=usecols,
            header=header,
            names=names,
        )

        ids = df_ids[self._id_column].dropna().astype(str).tolist()
        if self._limit is not None:
            ids = ids[: self._limit]

        if not ids:
            return []

        batch_size = self._source_config.resolve_effective_batch_size(
            limit=self._limit, hard_cap=25
        )

        return self._fetch_records(ids, batch_size)

    def _fetch_records(
        self, ids: list[str], batch_size: int
    ) -> Iterable[RawRecord]:
        all_records: list[RawRecord] = []

        for batch_ids in _chunk_list(ids, batch_size):
            self._logger.info(
                "Fetching batch from API", batch_size=len(batch_ids)
            )
            response = self._extraction_service.request_batch(
                self._entity, batch_ids, self._filter_key
            )
            batch_records = self._extraction_service.parse_response(response)
            serialized_records = self._extraction_service.serialize_records(
                self._entity, batch_records
            )
            all_records.extend(serialized_records)

        return all_records

    @staticmethod
    def _ensure_csv_options(
        options: dict[str, Any] | CsvInputOptions,
    ) -> CsvInputOptions:
        if isinstance(options, CsvInputOptions):
            return options
        return CsvInputOptions(**options)
