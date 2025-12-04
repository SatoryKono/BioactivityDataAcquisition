from pathlib import Path

from pathlib import Path

import pandas as pd

from bioetl.clients.csv_record_source import CsvRecordSource, IdListRecordSource
from bioetl.infrastructure.config.models import ChemblSourceConfig, CsvInputOptions


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


class _DummyLogger:
    def info(self, *args, **kwargs):  # pragma: no cover
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

    source = CsvRecordSource(
        input_path=csv_path,
        csv_options=CsvInputOptions(),
        limit=1,
        logger=_DummyLogger(),
    )

    records = list(source.iter_records())

    assert len(records) == 1
    expected = pd.DataFrame([{"id": 1, "name": "alpha"}])
    pd.testing.assert_frame_equal(records[0], expected)


def test_id_list_record_source_fetches_batches(tmp_path: Path) -> None:
    csv_path = tmp_path / "ids.csv"
    pd.DataFrame({"activity_id": ["A1", "A2", "A3", "A4"]}).to_csv(
        csv_path, index=False
    )

    extraction = _StubExtractionService()
    source = IdListRecordSource(
        input_path=csv_path,
        id_column="activity_id",
        csv_options=CsvInputOptions(),
        limit=3,
        extraction_service=extraction,
        source_config=ChemblSourceConfig(
            base_url="https://example.org",
            batch_size=2,
            timeout_sec=1,
            max_retries=1,
            rate_limit_per_sec=1.0,
        ),
        entity="activity",
        filter_key="activity_id__in",
        logger=_DummyLogger(),
    )

    records = list(source.iter_records())

    assert extraction.batches == [["A1", "A2"], ["A3"]]
    assert len(records) == 2
    combined = pd.concat(records, ignore_index=True)
    expected = pd.DataFrame({"id": ["A1", "A2", "A3"]})
    pd.testing.assert_frame_equal(combined, expected)
