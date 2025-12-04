import pandas as pd

from bioetl.domain.record_source import ApiRecordSource, InMemoryRecordSource, RawRecord


class _DummyExtractionService:
    def __init__(self) -> None:
        self.called_with: dict[str, str] | None = None

    def extract_all(self, entity: str, **filters: str) -> pd.DataFrame:  # type: ignore[override]
        self.called_with = {"entity": entity, **filters}
        return pd.DataFrame([
            {"id": "1", "name": "alpha"},
            {"id": "2", "name": "beta"},
        ])

    def get_release_version(self) -> str:  # pragma: no cover
        return "v1"

    def request_batch(self, entity: str, batch_ids: list[str], filter_key: str):  # pragma: no cover
        raise NotImplementedError

    def parse_response(self, raw_response):  # pragma: no cover
        raise NotImplementedError

    def serialize_records(self, entity: str, records: list[dict[str, str]]):  # pragma: no cover
        raise NotImplementedError


def test_in_memory_record_source_iterates_stably() -> None:
    records: list[RawRecord] = [
        {"id": "1", "value": "a"},
        {"id": "2", "value": "b"},
    ]
    source = InMemoryRecordSource(records)

    first_pass = list(source.iter_records())
    second_pass = list(source.iter_records())

    assert len(first_pass) == len(second_pass) == 1
    pd.testing.assert_frame_equal(first_pass[0], pd.DataFrame(records))
    pd.testing.assert_frame_equal(second_pass[0], pd.DataFrame(records))


def test_api_record_source_returns_serialized_records() -> None:
    extraction = _DummyExtractionService()
    source = ApiRecordSource(
        extraction_service=extraction,
        entity="activity",
        filters={"limit": 1},
    )

    records = list(source.iter_records())

    assert extraction.called_with == {"entity": "activity", "limit": 1}
    assert len(records) == 1
    expected_df = pd.DataFrame(
        [
            {"id": "1", "name": "alpha"},
            {"id": "2", "name": "beta"},
        ]
    )
    pd.testing.assert_frame_equal(records[0], expected_df)
