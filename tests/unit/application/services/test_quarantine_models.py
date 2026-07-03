"""Unit tests for immutable quarantine admin record views."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from bioetl.application.services._quarantine_models import QuarantineRecord

pytestmark = pytest.mark.unit


def test_quarantine_record_freezes_nested_payload_and_metadata() -> None:
    record = QuarantineRecord(
        error_code="DQ_INVALID",
        payload={"id": 1, "nested": {"tags": ["a", "b"]}},
        batch_id="batch-1",
        pipeline="chembl_activity",
        ingestion_ts=datetime(2026, 6, 19, 12, 0, tzinfo=UTC),
        metadata={"details": {"field": "title"}},
    )

    assert record.payload["id"] == 1
    assert record.payload["nested"]["tags"] == ("a", "b")
    assert record.metadata["details"]["field"] == "title"

    with pytest.raises(TypeError):
        record.payload["new"] = "value"  # type: ignore[index]
    with pytest.raises(TypeError):
        record.payload["nested"]["tags"] += ("c",)  # type: ignore[index]
    with pytest.raises(TypeError):
        record.metadata["details"]["field"] = "other"  # type: ignore[index]
