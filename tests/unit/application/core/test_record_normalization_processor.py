"""Unit tests for application-owned record normalization stage."""

from __future__ import annotations

import pytest

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.domain.transformations import generate_content_hash


@pytest.mark.unit
def test_normalize_record_applies_identifier_date_json_and_hash_rules() -> None:
    processor = RecordNormalizationProcessor(provider="crossref")
    record = {
        "entity_id": "crossref:raw",
        "content_hash": "stale",
        "publication_doi": " HTTPS://doi.org/10.1000/ABC ",
        "publication_pmid": 12345,
        "publication_date": "2024-02",
        "title": "  Example <b>Title</b>  ",
        "payload": {"b": 1, "a": [2, 1]},
        "_run_id": "keep-me",
    }

    normalized = processor.normalize_record(record)

    assert normalized["entity_id"] == "crossref:raw"
    assert normalized["_run_id"] == "keep-me"
    assert normalized["publication_doi"] == "10.1000/abc"
    assert normalized["publication_pmid"] == "12345"
    assert normalized["publication_date"] == "2024-02-29"
    assert normalized["title"] == "Example Title"
    assert normalized["payload"] == '{"a":[2,1],"b":1}'
    assert normalized["content_hash"] == str(
        generate_content_hash(
            normalized,
            "crossref",
            exclude_none=True,
            exclude_fields={"entity_id", "content_hash"},
        )
    )


@pytest.mark.unit
def test_compute_content_hash_is_idempotent_for_normalized_payload() -> None:
    processor = RecordNormalizationProcessor(provider="crossref")
    normalized_payload = {
        "entity_id": "crossref:1",
        "content_hash": "stale",
        "title": "Example Title",
        "payload": '{"a":1,"b":2}',
        "_run_id": "keep-me",
    }

    first_hash = processor.compute_content_hash(normalized_payload)
    second_hash = processor.compute_content_hash(normalized_payload)

    assert first_hash == second_hash


def test_normalize_record_leaves_invalid_json_like_strings_as_trimmed_text() -> None:
    processor = RecordNormalizationProcessor(provider="crossref")

    normalized = processor.normalize_record(
        {"entity_id": "crossref:1", "content_hash": "stale", "raw_json": "{not json}"}
    )

    assert normalized["raw_json"] == "{not json}"
