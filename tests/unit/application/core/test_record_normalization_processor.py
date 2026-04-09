"""Unit tests for application-owned record normalization stage."""

from __future__ import annotations

import json

import pytest
from hypothesis import given
from hypothesis import strategies as st

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
            affects_hash=True,
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
            affects_hash=True,
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
    assert (
        silver_record["content_hash"]
        == silver_record["_content_hashes_by_version"]["2.0.0"]
    )
    assert (
        silver_record["_content_hashes_by_version"]["1.0.0"]
        != silver_record["content_hash"]
    )


@pytest.mark.unit
def test_finalize_pre_silver_skips_versioned_hash_projection_when_rollout_does_not_affect_hash() -> (
    None
):
    processor = RecordNormalizationProcessor(
        provider="crossref",
        content_hash_policy_by_version=ContentHashPolicyByVersion(
            active_version="2.0.0",
            affects_hash=False,
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
    assert "_content_hashes_by_version" not in silver_record


@pytest.mark.unit
def test_profile_auto_resolves_for_chembl_activity() -> None:
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="activity",
    )

    normalized = processor.normalize_business_data(
        {
            "activity_id": " CHEMBL25 ",
            "publication_doi": " HTTPS://doi.org/10.1000/ABC ",
            "activity_properties": ' [{"rank":2,"kind":"b"},{"kind":"a","rank":1}] ',
        }
    )

    assert processor.profile is not None
    assert normalized["activity_id"] == "CHEMBL25"
    assert normalized["publication_doi"] == "10.1000/abc"
    assert normalized["activity_properties"] == '[{"kind":"b","rank":2},{"kind":"a","rank":1}]'


@pytest.mark.unit
def test_chembl_activity_profile_makes_content_hash_invariant_for_set_like_json_arrays() -> None:
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="activity",
    )
    record_a = {
        "entity_id": "chembl:1",
        "content_hash": "stale-a",
        "activity_id": "CHEMBL25",
        "publication_doi": "10.1000/abc",
        "activity_properties": '[{"kind":"a","rank":1},{"kind":"b","rank":2}]',
        "_run_id": "run-a",
    }
    record_b = {
        "entity_id": "chembl:1",
        "content_hash": "stale-b",
        "activity_id": "CHEMBL25",
        "publication_doi": "10.1000/abc",
        "activity_properties": '[{"kind":"b","rank":2},{"kind":"a","rank":1}]',
        "_run_id": "run-b",
    }

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)

    assert normalized_a["content_hash"] == normalized_b["content_hash"]


@pytest.mark.unit
def test_chembl_activity_content_hash_matches_golden_value() -> None:
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="activity",
    )

    normalized = processor.normalize_record(
        {
            "entity_id": "chembl:1",
            "content_hash": "stale",
            "activity_id": " CHEMBL25 ",
            "publication_doi": " HTTPS://doi.org/10.1000/ABC ",
            "publication_pmid": " 12345 ",
            "standard_value": "1.2300000000",
            "activity_properties": (
                ' [{"kind":"b","rank":2},{"rank":1,"kind":"a"}] '
            ),
            "_run_id": "run-1",
        }
    )

    assert (
        normalized["content_hash"]
        == "c066788d40b9881e1872940148940e127e498ca83dad4cecc88bab05abf34972"
    )


@pytest.mark.unit
def test_chembl_activity_content_hash_ignores_meta_fields_and_equivalent_scalars() -> None:
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="activity",
    )
    record_a = {
        "entity_id": "chembl:1",
        "content_hash": "stale-a",
        "activity_id": "CHEMBL25",
        "publication_doi": "https://doi.org/10.1000/ABC",
        "publication_pmid": "0012345",
        "standard_value": "1.2300000000",
        "activity_properties": '[{"kind":"a","rank":1},{"kind":"b","rank":2}]',
        "_run_id": "run-a",
        "_source_batch_id": "batch-a",
        "_index": 1,
    }
    record_b = {
        "entity_id": "chembl:2",
        "content_hash": "stale-b",
        "activity_id": "CHEMBL25",
        "publication_doi": "10.1000/abc",
        "publication_pmid": 12345,
        "standard_value": 1.23,
        "activity_properties": '[{"kind":"b","rank":2},{"kind":"a","rank":1}]',
        "_run_id": "run-b",
        "_source_batch_id": "batch-b",
        "_index": 999,
    }

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)

    assert normalized_a["content_hash"] == normalized_b["content_hash"]
    assert normalized_a["publication_pmid"] == "12345"
    assert normalized_b["publication_pmid"] == "12345"


@pytest.mark.unit
def test_chembl_activity_content_hash_treats_blank_identifier_fields_like_none() -> None:
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="activity",
    )
    record_a = {
        "entity_id": "chembl:1",
        "content_hash": "stale-a",
        "activity_id": "CHEMBL25",
        "publication_doi": "   ",
        "publication_pmid": None,
        "standard_value": "1.23",
    }
    record_b = {
        "entity_id": "chembl:1",
        "content_hash": "stale-b",
        "activity_id": "CHEMBL25",
        "publication_doi": None,
        "publication_pmid": "",
        "standard_value": 1.23,
    }

    normalized_a = processor.normalize_record(record_a)
    normalized_b = processor.normalize_record(record_b)

    assert normalized_a["publication_doi"] is None
    assert normalized_b["publication_pmid"] is None
    assert normalized_a["content_hash"] == normalized_b["content_hash"]


@pytest.mark.unit
@given(
    activity_properties=st.permutations(
        (
            {"kind": "a", "rank": 1},
            {"kind": "b", "rank": 2},
            {"kind": "c", "rank": 3},
        )
    )
)
def test_chembl_activity_content_hash_is_permutation_invariant_for_set_like_json(
    activity_properties: tuple[dict[str, object], ...],
) -> None:
    processor = RecordNormalizationProcessor(
        provider="chembl",
        entity_type="activity",
    )
    base_record = {
        "entity_id": "chembl:1",
        "content_hash": "stale",
        "activity_id": "CHEMBL25",
        "publication_doi": "10.1000/abc",
        "standard_value": 1.23,
        "_run_id": "run-1",
    }
    canonical = processor.normalize_record(
        {
            **base_record,
            "activity_properties": (
                '[{"kind":"a","rank":1},{"kind":"b","rank":2},{"kind":"c","rank":3}]'
            ),
        }
    )
    candidate = processor.normalize_record(
        {
            **base_record,
            "activity_properties": json.dumps(list(activity_properties)),
        }
    )

    assert canonical["content_hash"] == candidate["content_hash"]
