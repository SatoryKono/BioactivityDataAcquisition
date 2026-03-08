"""Tests for domain type aliases and identifiers.

Tests for NewType definitions and TypeAlias exports.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from bioetl.domain.types.identifiers import (
    BatchID,
    ContentHash,
    EntityID,
    RunID,
    SilverRecord,
)


@pytest.mark.unit
class TestNewTypeIdentifiers:
    """Tests for NewType-based identifiers."""

    def test_run_id_wraps_uuid(self) -> None:
        uid = uuid4()
        run_id = RunID(uid)
        assert isinstance(run_id, UUID)

    def test_entity_id_wraps_str(self) -> None:
        eid = EntityID("CHEMBL123")
        assert isinstance(eid, str)
        assert eid == "CHEMBL123"

    def test_content_hash_wraps_str(self) -> None:
        ch = ContentHash("sha256abcdef")
        assert isinstance(ch, str)

    def test_batch_id_wraps_uuid(self) -> None:
        uid = uuid4()
        bid = BatchID(uid)
        assert isinstance(bid, UUID)


@pytest.mark.unit
class TestSilverRecord:
    """Tests for SilverRecord TypedDict."""

    def test_silver_record_creation(self) -> None:
        record: SilverRecord = {
            "entity_id": "test:001",
            "content_hash": "abc123",
        }
        assert record["entity_id"] == "test:001"

    def test_silver_record_partial(self) -> None:
        # total=False means all fields are optional
        record: SilverRecord = {}
        assert isinstance(record, dict)
