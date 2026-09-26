# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.ledger.rich_events import (
    RunLedgerRichEventRecordingMixin,
    record_composite_dependency_completed,
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
        self.appended.append(
            {
                "event_type": event_type,
                "status": status,
                "stage": stage,
                "details": details,
            }
        )
        return RunLedgerEntry(
            entry_id=f"entry-{len(self.appended)}",
            manifest_id="manifest-1",
            run_id=RunID(UUID("00000000-0000-0000-0000-000000000701")),
            event_type=event_type,
            occurred_at=FIXED_TEST_TIME,
            status=status,
            stage=stage,
            details=details,
        )


def test_record_composite_dependency_completed_normalizes_payload() -> None:
    appender = _FakeAppender()

    entry = record_composite_dependency_completed(
        appender,
        dependency_name=" chembl_target ",
        result={"status": "success", "row_count": 4},
    )

    assert entry.event_type == "composite_dependency_completed"
    assert entry.status == "success"
    assert entry.stage == "dependencies"
    assert entry.details == {
        "status": "success",
        "row_count": 4,
        "dependency_name": "chembl_target",
        "pipeline_name": "chembl_target",
    }


def test_record_input_snapshot_published_mixin_omits_missing_query_fingerprint() -> (
    None
):
    appender = _FakeAppender()

    entry = appender.record_input_snapshot_published(
        provider="chembl",
        entity="activity",
        pipeline_name="chembl_activity",
        snapshot_id="sha256:abc",
        content_hash="abc",
        immutable_uri="vcr://chembl/activity",
        bronze_batch_ref="bronze-batch-1",
        details={"row_count": 3},
    )

    assert entry.event_type == "input_snapshot_published"
    assert entry.status == "published"
    assert entry.stage == "bronze"
    assert entry.details == {
        "provider": "chembl",
        "entity": "activity",
        "pipeline_name": "chembl_activity",
        "snapshot_id": "sha256:abc",
        "content_hash": "abc",
        "immutable_uri": "vcr://chembl/activity",
        "bronze_batch_ref": "bronze-batch-1",
        "row_count": 3,
    }
    assert "query_fingerprint" not in entry.details


def test_record_input_snapshot_published_requires_provider() -> None:
    with pytest.raises(ValueError, match="provider is required"):
        record_input_snapshot_published(
            _FakeAppender(),
            provider="  ",
            entity="activity",
            pipeline_name="chembl_activity",
            snapshot_id="sha256:abc",
            content_hash="abc",
            immutable_uri="vcr://chembl/activity",
            bronze_batch_ref="bronze-batch-1",
        )
