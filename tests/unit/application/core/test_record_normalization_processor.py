"""Unit tests for application-owned record normalization stage."""

from __future__ import annotations

import pytest

from bioetl.application.core.config import (
    ContentHashPolicyByVersion,
    ContentHashVersionPolicy,
)
from bioetl.application.core.pre_silver_record import PreSilverRecord
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


@pytest.mark.unit
def test_compute_content_hashes_by_version_returns_ordered_multi_hash_payload() -> None:
    processor = RecordNormalizationProcessor(
        provider="crossref",
        content_hash_policy_by_version=ContentHashPolicyByVersion(
            active_version="2.0.0",
            policies=(
                ContentHashVersionPolicy(
                    version="1.0.0",
                    include_fields=frozenset({"title"}),
                    exclude_fields=frozenset(),
                ),
                ContentHashVersionPolicy(
                    version="2.0.0",
                    include_fields=frozenset({"title", "journal"}),
                    exclude_fields=frozenset(),
                ),
            ),
        ),
    )

    payload = {"entity_id": "crossref:1", "title": "Example", "journal": "Nature"}

    hashes = processor.compute_content_hashes_by_version(payload)

    assert tuple(hashes) == ("1.0.0", "2.0.0")
    assert hashes["1.0.0"] != hashes["2.0.0"]


@pytest.mark.unit
def test_finalize_pre_silver_attaches_active_and_versioned_content_hashes() -> None:
    processor = RecordNormalizationProcessor(
        provider="crossref",
        content_hash_policy_by_version=ContentHashPolicyByVersion(
            active_version="2.0.0",
            policies=(
                ContentHashVersionPolicy(
                    version="1.0.0",
                    include_fields=frozenset({"title"}),
                    exclude_fields=frozenset(),
                ),
                ContentHashVersionPolicy(
                    version="2.0.0",
                    include_fields=frozenset({"title", "journal"}),
                    exclude_fields=frozenset(),
                ),
            ),
        ),
    )
    pre_silver = PreSilverRecord(
        entity_id="crossref:1",
        business_data={"title": "Example", "journal": "Nature"},
        build_silver_record=lambda _context, entity_id, content_hash, index, business: {
            "entity_id": entity_id,
            "content_hash": content_hash,
            "_index": index,
            **business,
        },
    )

    silver_record = processor.finalize_pre_silver(
        pre_silver,
        context=object(),
        index=0,
    )

    assert silver_record is not None
    assert silver_record["content_hash"] == silver_record["_content_hashes_by_version"]["2.0.0"]
    assert silver_record["_content_hashes_by_version"]["1.0.0"] != silver_record["content_hash"]
