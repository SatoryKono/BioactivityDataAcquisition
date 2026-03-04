"""Unit tests for BaseEntity — validates system field invariants."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.domain.entities.base import BaseEntity


BASE_KWARGS = {
    "entity_id": "test:entity:001",
    "content_hash": "sha256hash",
    "run_id": "run-001",
    "run_type": "incremental",
    "ingestion_ts": datetime(2024, 1, 1, tzinfo=UTC),
    "_index": 0,
}


@pytest.mark.unit
class TestBaseEntity:
    """Tests for BaseEntity system field invariants."""

    def test_valid_creation(self) -> None:
        e = BaseEntity(**BASE_KWARGS)
        assert e.entity_id == "test:entity:001"
        assert e.content_hash == "sha256hash"
        assert e.run_id == "run-001"
        assert e._index == 0
        assert e.source_batch_id is None
        assert e._dq_warn is False
        assert e._dq_error is False

    def test_with_source_batch_id(self) -> None:
        e = BaseEntity(**BASE_KWARGS, source_batch_id="batch-001")
        assert e.source_batch_id == "batch-001"

    def test_with_dq_flags(self) -> None:
        e = BaseEntity(**BASE_KWARGS, _dq_warn=True, _dq_error=True)
        assert e._dq_warn is True
        assert e._dq_error is True

    def test_empty_entity_id_raises(self) -> None:
        kwargs = {**BASE_KWARGS, "entity_id": ""}
        with pytest.raises(ValueError, match="Entity ID cannot be empty"):
            BaseEntity(**kwargs)

    def test_empty_content_hash_raises(self) -> None:
        kwargs = {**BASE_KWARGS, "content_hash": ""}
        with pytest.raises(ValueError, match="Content hash cannot be empty"):
            BaseEntity(**kwargs)

    def test_negative_index_raises(self) -> None:
        kwargs = {**BASE_KWARGS, "_index": -1}
        with pytest.raises(ValueError, match="_index cannot be negative"):
            BaseEntity(**kwargs)

    def test_zero_index_valid(self) -> None:
        e = BaseEntity(**BASE_KWARGS)
        assert e._index == 0

    def test_large_index_valid(self) -> None:
        e = BaseEntity(**{**BASE_KWARGS, "_index": 999999})
        assert e._index == 999999

    def test_immutable(self) -> None:
        e = BaseEntity(**BASE_KWARGS)
        with pytest.raises((AttributeError, TypeError)):
            e.entity_id = "new_id"  # type: ignore[misc]

    def test_immutable_dq_flags(self) -> None:
        e = BaseEntity(**BASE_KWARGS)
        with pytest.raises((AttributeError, TypeError)):
            e._dq_warn = True  # type: ignore[misc]
