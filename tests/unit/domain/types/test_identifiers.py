# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for domain type aliases and identifiers.

Tests for NewType definitions and TypeAlias exports.
"""

from __future__ import annotations

from uuid import UUID

import pytest

from bioetl.domain.types.identifiers import (
    BatchID,
    ContentHash,
    EntityID,
    RunID,
    SilverRecord,
)

RUN_ID_VALUE = UUID("00000000-0000-4000-8000-000000000001")
BATCH_ID_VALUE = UUID("00000000-0000-4000-8000-000000000002")


@pytest.mark.unit
class TestNewTypeIdentifiers:
    """Tests for NewType-based identifiers."""

    def test_run_id_wraps_uuid(self) -> None:
        run_id = RunID(RUN_ID_VALUE)
        assert isinstance(run_id, UUID)

    def test_entity_id_wraps_str(self) -> None:
        eid = EntityID("CHEMBL123")
        assert isinstance(eid, str)
        assert eid == "CHEMBL123"

    def test_content_hash_wraps_str(self) -> None:
        ch = ContentHash("sha256abcdef")
        assert isinstance(ch, str)

    def test_batch_id_wraps_uuid(self) -> None:
        bid = BatchID(BATCH_ID_VALUE)
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
