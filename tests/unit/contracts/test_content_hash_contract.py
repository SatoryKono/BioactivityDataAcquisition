"""Contract tests for content-hash normalization and exclusion rules."""

from __future__ import annotations

from datetime import datetime

from bioetl.domain.services import EntityIdentityGenerator
from bioetl.domain.transformations import generate_content_hash


def test_content_hash_normalization_contract() -> None:
    """Hash MUST be stable across normalization-equivalent values."""
    service = EntityIdentityGenerator()

    record_a = {
        "name": "  Alpha  ",
        "score": 3.141592653589793,
        "measured_at": datetime(2025, 1, 1, 10, 0, 0),
    }
    record_b = {
        "name": "Alpha",
        "score": 3.1415926536,
        "measured_at": datetime(2025, 1, 1, 22, 15, 0),
    }

    assert service.compute_content_hash(
        "chembl", record_a
    ) == service.compute_content_hash("chembl", record_b)


def test_content_hash_excludes_meta_and_dq_prefix_contract() -> None:
    """Meta fields and _dq_* fields MUST NOT influence content hash."""
    service = EntityIdentityGenerator()

    base = {"activity_id": "A1", "value": 10}
    with_meta = {
        **base,
        "_run_id": "run-1",
        "_ingestion_ts": "2026-01-01T00:00:00Z",
        "_dq_custom_check": "warn",
    }

    assert service.compute_content_hash("chembl", base) == service.compute_content_hash(
        "chembl", with_meta
    )


def test_content_hash_excludes_occurrence_only_source_batch_id_contract() -> None:
    """Occurrence-only BatchID lineage metadata MUST NOT alter semantic identity."""
    service = EntityIdentityGenerator()

    base = {"activity_id": "A1", "value": 10}
    with_batch_a = {
        **base,
        "_source_batch_id": "11111111-1111-1111-1111-111111111111",
    }
    with_batch_b = {
        **base,
        "_source_batch_id": "22222222-2222-2222-2222-222222222222",
    }

    assert service.compute_content_hash(
        "chembl", with_batch_a
    ) == service.compute_content_hash("chembl", with_batch_b)


def test_content_hash_service_matches_canonical_transform_contract() -> None:
    """EntityIdentityGenerator MUST delegate to the canonical transformation path."""
    service = EntityIdentityGenerator()
    record = {
        "activity_id": "A1",
        "value": 10,
        "comment": "  stable  ",
        "nested": {"b": 2, "a": 1},
        "_run_id": "run-1",
    }

    assert service.compute_content_hash("chembl", record) == generate_content_hash(
        record, "chembl"
    )


def test_content_hash_future_meta_field_contract() -> None:
    """Future underscore-prefixed technical fields MUST NOT alter content hash."""
    service = EntityIdentityGenerator()

    base = {"activity_id": "A1", "value": 10}
    with_future_meta = {
        **base,
        "_future_meta_field": "v2",
        "_new_runtime_flag": True,
    }

    assert service.compute_content_hash("chembl", base) == service.compute_content_hash(
        "chembl", with_future_meta
    )


def test_content_hash_schema_include_exclude_contract() -> None:
    """Schema include/exclude policy MUST be applied by EntityIdentityGenerator."""
    service = EntityIdentityGenerator(
        content_hash_include_fields={"activity_id", "value", "ignore_me"},
        content_hash_exclude_fields={"ignore_me"},
    )

    record_v1 = {
        "activity_id": "A1",
        "value": 10,
        "comment": "v1",
        "ignore_me": "foo",
    }
    record_v2 = {
        "activity_id": "A1",
        "value": 10,
        "comment": "v2",
        "ignore_me": "bar",
    }

    assert service.compute_content_hash(
        "chembl", record_v1
    ) == service.compute_content_hash("chembl", record_v2)
