"""CSV-based record source implementations."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from pathlib import Path
from typing import Any

import pandas as pd

from bioetl.domain.clients.base.logging.contracts import LoggerAdapterABC
from bioetl.domain.configs import ChemblSourceConfig, CsvInputOptions
from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.record_source import RawRecord, RecordSource


def _chunk_list(data: list[Any], size: int) -> Iterator[list[Any]]:
    for i in range(0, len(data), size):
        yield data[i : i + size]


class CsvRecordSourceImpl(RecordSource):
    """Record source that reads full datasets from CSV."""

    def __init__(
        self,
        input_path: Path,
        csv_options: dict[str, Any] | CsvInputOptions,
        limit: int | None,
        logger: LoggerAdapterABC,
        chunk_size: int | None = None,
    ) -> None:
        self._input_path = input_path
        self._csv_options = self._ensure_csv_options(csv_options)
        self._limit = limit
        self._logger = logger
        self._chunk_size = chunk_size

    def iter_records(self) -> Iterable[list[RawRecord]]:
        header = 0 if self._csv_options.header else None
        self._logger.info(f"Extracting records from CSV dataset: {self._input_path}")
        df = pd.read_csv(
            self._input_path,
            delimiter=self._csv_options.delimiter,
            header=header,
        )
        if self._limit is not None:
            df = df.head(self._limit)
        records: list[RawRecord] = df.to_dict(orient="records")
        if self._chunk_size is None or self._chunk_size <= 0:
            yield records
            return

        yield from _chunk_list(records, self._chunk_size)

    @staticmethod
    def _ensure_csv_options(
        options: dict[str, Any] | CsvInputOptions,
    ) -> CsvInputOptions:
        if isinstance(options, CsvInputOptions):
            return options
        return CsvInputOptions(**options)


class IdListRecordSourceImpl(RecordSource):
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
        chunk_size: int | None = None,
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
        self._chunk_size = chunk_size

    def iter_records(self) -> Iterable[list[RawRecord]]:
        header = 0 if self._csv_options.header else None
        usecols: list[Any] = [self._id_column] if self._csv_options.header else [0]
        names: list[str] | None = (
            [self._id_column] if not self._csv_options.header else None
        )

        try:
            df_ids = pd.read_csv(
                self._input_path,
                delimiter=self._csv_options.delimiter,
                usecols=usecols,
                header=header,
                names=names,
            )
        except (KeyError, ValueError) as exc:
            # KeyError when usecols specifies a column that doesn't exist
            # ValueError when pandas can't parse the column
            raise ValueError(
                (
                    f"Required ID column '{self._id_column}' not found in CSV file: "
                    f"{self._input_path}"
                )
            ) from exc

        # Additional validation: ensure the column exists after reading
        if self._csv_options.header and self._id_column not in df_ids.columns:
            raise ValueError(
                (
                    f"Required ID column '{self._id_column}' not found in CSV file: "
                    f"{self._input_path}"
                )
            )

        ids = df_ids[self._id_column].dropna().astype(str).tolist()
        if self._limit is not None:
            ids = ids[: self._limit]

        if not ids:
            return

        batch_size = self._source_config.resolve_effective_batch_size(
            limit=self._limit, hard_cap=25
        )

        yield from self._fetch_records(ids, batch_size)

    def _fetch_records(
        self, ids: list[str], batch_size: int
    ) -> Iterable[list[RawRecord]]:
        for batch_ids in _chunk_list(ids, batch_size):
            self._logger.info("Fetching batch from API", batch_size=len(batch_ids))
            response = self._extraction_service.request_batch(
                self._entity, batch_ids, self._filter_key
            )
            batch_records = self._extraction_service.parse_response(response)
            serialized_records = self._extraction_service.serialize_records(
                self._entity, batch_records
            )
            if self._chunk_size is None or self._chunk_size <= 0:
                yield serialized_records
                continue

            yield from _chunk_list(serialized_records, self._chunk_size)

    @staticmethod
    def _ensure_csv_options(
        options: dict[str, Any] | CsvInputOptions,
    ) -> CsvInputOptions:
        if isinstance(options, CsvInputOptions):
            return options
        return CsvInputOptions(**options)
