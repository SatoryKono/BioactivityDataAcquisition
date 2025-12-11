from pathlib import Path
from typing import cast

import pandas as pd
from pydantic import AnyHttpUrl

from bioetl.application.files.csv_record_source import (
    CsvRecordSourceImpl,
    IdListRecordSourceImpl,
)
from bioetl.domain.configs import (
    ChemblSourceConfig,
    ClientConfig,
    CsvInputConfig,
)
from bioetl.domain.observability.contracts import LoggingPortABC
from bioetl.domain.ports.extraction import ExtractionServiceABC
from bioetl.domain.schemas.chembl.raw_models import ActivityRawModel


class _StubExtractionService:
    def __init__(self) -> None:
        self.batches: list[list[str]] = []

    def get_release_version(self) -> str:  # pragma: no cover
        return "v1"

    def extract_all(self, entity: str, **filters):  # pragma: no cover
        raise NotImplementedError

    def request_batch(self, entity: str, batch_ids: list[str], filter_key: str):
        self.batches.append(batch_ids)
        return {
            "records": [
                {
                    "activity_id": value.lstrip("A") if value.startswith("A") else value,
                    "standard_flag": True,
                    "standard_value": 1.0
                } for value in batch_ids
            ]
        }

    def parse(self, raw_response: dict[str, list[dict[str, str]]]):
        return [
            ActivityRawModel.model_validate({
                **item,
                "standard_value": item.get("standard_value", 1.0) if item.get("standard_flag") else None
            }) for item in raw_response["records"]
        ]

    def parse_response(self, raw_response: dict[str, list[dict[str, str]]]):
        return self.parse(raw_response)

    def serialize_records(
        self, entity: str, records: list[ActivityRawModel]
    ) -> list[ActivityRawModel]:
        return records


class _DummyLogger(LoggingPortABC):
    def info(self, *args, **kwargs):  # pragma: no cover
        return None

    def error(self, *args, **kwargs):  # pragma: no cover
        return None

    def debug(self, *args, **kwargs):  # pragma: no cover
        return None

    def warning(self, *args, **kwargs):  # pragma: no cover
        return None

    def apply_bind(self, **kwargs):  # pragma: no cover
        return self


def test_csv_record_source_reads_dataset(tmp_path: Path) -> None:
    csv_path = tmp_path / "dataset.csv"
    pd.DataFrame(
        [
            {"activity_id": "1", "standard_flag": True},
            {"activity_id": "2", "standard_flag": False},
        ]
    ).to_csv(csv_path, index=False)

    source = CsvRecordSourceImpl(
        input_path=csv_path,
        csv_options=CsvInputConfig(),
        limit=1,
        logger=cast(LoggingPortABC, _DummyLogger()),
        model_cls=ActivityRawModel,
    )

    chunks = list(source.iter_records())

    assert len(chunks) == 1
    # CsvRecordSource returns raw dicts, ignores model_cls (but warns)
    # Pandas reads "1" as int 1 by default
    expected = [{"activity_id": 1, "standard_flag": True}]
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
        client=ClientConfig(
            timeout_sec=1,
            max_retries=0,
            rate_limit_per_sec=1.0,
        ),
        batch_size=2,
    )
    source = IdListRecordSourceImpl(
        input_path=csv_path,
        id_column="activity_id",
        csv_options=CsvInputConfig(),
        limit=3,
        extraction_service=cast(ExtractionServiceABC, extraction),
        source_config=source_config,
        entity="activity",
        filter_key="activity_id__in",
        logger=cast(LoggingPortABC, _DummyLogger()),
    )

    records = list(source.iter_records())

    assert extraction.batches == [["A1", "A2"], ["A3"]]
    assert len(records) == 2
    combined = [record for batch in records for record in batch]
    expected = [
        ActivityRawModel(activity_id="1", standard_flag=True, standard_value=1.0),
        ActivityRawModel(activity_id="2", standard_flag=True, standard_value=1.0),
        ActivityRawModel(activity_id="3", standard_flag=True, standard_value=1.0),
    ]
    assert combined == expected
