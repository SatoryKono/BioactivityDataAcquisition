"""Additional behavioral tests for bounded rich ledger event helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.ledger.rich_events import (
    RunLedgerRichEventRecordingMixin,
    record_composite_enricher_completed,
    record_composite_merge_completed,
    record_input_snapshot_published,
)
from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.types import RunID
from tests.helpers.clock import FIXED_TEST_TIME


pytestmark = pytest.mark.unit


@dataclass
class _FakeAppender(RunLedgerRichEventRecordingMixin):
    appended: list[dict[str, object]] = field(default_factory=list)

    def _append(
        self,
        *,
        event_type: str,
        status: str | None,
        stage: str | None = None,
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry:
        payload = {
            "event_type": event_type,
            "status": status,
            "stage": stage,
            "details": details,
        }
        self.appended.append(payload)
        return RunLedgerEntry(
            entry_id=f"entry-{len(self.appended)}",
            manifest_id="manifest-1",
            run_id=RunID(UUID("00000000-0000-0000-0000-000000000801")),
            event_type=event_type,
            occurred_at=FIXED_TEST_TIME,
            status=status,
            stage=stage,
            details=details,
        )


@pytest.mark.unit
def test_record_composite_enricher_completed_defaults_completed_status() -> None:
    appender = _FakeAppender()

    entry = record_composite_enricher_completed(
        appender,
        enricher_name=" mesh ",
        result={"row_count": 7},
    )

    assert entry.event_type == "composite_enricher_completed"
    assert entry.status == "completed"
    assert entry.stage == "enrichment"
    assert entry.details == {
        "row_count": 7,
        "enricher_name": "mesh",
    }


@pytest.mark.unit
def test_record_composite_merge_completed_preserves_payload_and_stage() -> None:
    appender = _FakeAppender()

    entry = record_composite_merge_completed(
        appender,
        result={"merged_rows": 12, "strategy": "left_outer"},
    )

    assert entry.event_type == "composite_merge_completed"
    assert entry.status == "completed"
    assert entry.stage == "merge"
    assert entry.details == {
        "merged_rows": 12,
        "strategy": "left_outer",
    }


@pytest.mark.unit
def test_record_input_snapshot_published_includes_query_fingerprint_and_extra_details() -> (
    None
):
    entry = record_input_snapshot_published(
        _FakeAppender(),
        provider="chembl",
        entity="activity",
        pipeline_name="chembl_activity",
        snapshot_id="sha256:def",
        content_hash="def",
        immutable_uri="vcr://chembl/activity",
        bronze_batch_ref="bronze-batch-2",
        query_fingerprint="fp-activity",
        details={"row_count": 5, "published_by": "worker-1"},
    )

    assert entry.details == {
        "provider": "chembl",
        "entity": "activity",
        "pipeline_name": "chembl_activity",
        "snapshot_id": "sha256:def",
        "content_hash": "def",
        "immutable_uri": "vcr://chembl/activity",
        "bronze_batch_ref": "bronze-batch-2",
        "query_fingerprint": "fp-activity",
        "row_count": 5,
        "published_by": "worker-1",
    }
