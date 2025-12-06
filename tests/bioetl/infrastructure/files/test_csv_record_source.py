from pathlib import Path
from typing import cast

from pathlib import Path
from typing import cast

import pandas as pd
from pydantic import AnyHttpUrl

from bioetl.domain.contracts import ExtractionServiceABC
from bioetl.domain.observability import LoggingPort
from bioetl.infrastructure.config.models import (
    ChemblSourceConfig,
    CsvInputOptions,
)
from bioetl.infrastructure.files.csv_record_source import (
    CsvRecordSourceImpl,
    IdListRecordSourceImpl,
)


class _StubExtractionService:
    def __init__(self) -> None:
        self.batches: list[list[str]] = []

    def get_release_version(self) -> str:  # pragma: no cover
        return "v1"

    def extract_all(self, entity: str, **filters):  # pragma: no cover
        raise NotImplementedError

    def request_batch(self, entity: str, batch_ids: list[str], filter_key: str):
        self.batches.append(batch_ids)
        return {"records": [{"id": value} for value in batch_ids]}

    def parse_response(self, raw_response: dict[str, list[dict[str, str]]]):
        return raw_response["records"]

    def serialize_records(self, entity: str, records: list[dict[str, str]]):
        return records


class _DummyLogger(LoggingPort):
    def info(self, *args, **kwargs):  # pragma: no cover
        return None

    def error(self, *args, **kwargs):  # pragma: no cover
        return None

    def debug(self, *args, **kwargs):  # pragma: no cover
        return None

    def warning(self, *args, **kwargs):  # pragma: no cover
        return None

    def bind(self, **kwargs):  # pragma: no cover
        return self


def test_csv_record_source_reads_dataset(tmp_path: Path) -> None:
    csv_path = tmp_path / "dataset.csv"
    pd.DataFrame([{"id": 1, "name": "alpha"}, {"id": 2, "name": "beta"}]).to_csv(
        csv_path, index=False
    )

    source = CsvRecordSourceImpl(
        input_path=csv_path,
        csv_options=CsvInputOptions(),
        limit=1,
        logger=cast(LoggingPort, _DummyLogger()),
    )

    chunks = list(source.iter_records())

    assert len(chunks) == 1
    expected = [{"id": 1, "name": "alpha"}]
    assert chunks[0] == expected


def test_id_list_record_source_fetches_batches(tmp_path: Path) -> None:
    csv_path = tmp_path / "ids.csv"
    pd.DataFrame({"activity_id": ["A1", "A2", "A3", "A4"]}).to_csv(
        csv_path, index=False
    )

    extraction = _StubExtractionService()
    source_config = ChemblSourceConfig(
        provider="chembl",
        base_url=cast(AnyHttpUrl, "https://example.org"),
        timeout_sec=1,
        max_retries=0,
        rate_limit_per_sec=1.0,
        batch_size=2,
    )
    source = IdListRecordSourceImpl(
        input_path=csv_path,
        id_column="activity_id",
        csv_options=CsvInputOptions(),
        limit=3,
        extraction_service=cast(ExtractionServiceABC, extraction),
        source_config=source_config,
        entity="activity",
        filter_key="activity_id__in",
        logger=cast(LoggingPort, _DummyLogger()),
    )

    records = list(source.iter_records())

    assert extraction.batches == [["A1", "A2"], ["A3"]]
    assert len(records) == 2
    combined = [record for batch in records for record in batch]
    expected = [{"id": "A1"}, {"id": "A2"}, {"id": "A3"}]
    assert combined == expected
