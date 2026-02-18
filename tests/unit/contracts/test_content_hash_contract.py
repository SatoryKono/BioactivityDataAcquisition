"""Contract tests for content-hash normalization and exclusion rules."""

from __future__ import annotations

from datetime import datetime

from bioetl.domain.services import IdentityService


def test_content_hash_normalization_contract() -> None:
    """Hash MUST be stable across normalization-equivalent values."""
    service = IdentityService()

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
    service = IdentityService()

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


def test_content_hash_schema_include_exclude_contract() -> None:
    """Schema include/exclude policy MUST be applied by IdentityService."""
    service = IdentityService(
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
