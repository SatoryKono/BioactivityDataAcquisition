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
"""Unit tests for metadata lineage node builders."""

from __future__ import annotations

from datetime import UTC, datetime
from tests.helpers.deterministic_ids import (
    deterministic_batch_uuid_from_callsite,
    deterministic_run_uuid_from_callsite,
)

import pytest

from bioetl.application.services.lineage.metadata_lineage_node_builders import (
    fragment_timestamp,
    source_request_node,
    source_system_node,
)
from bioetl.domain.models.metadata import InputSnapshotRef, SourceMetadata
from bioetl.domain.ports import BronzeMetadataInput
from bioetl.domain.types import RunType
from bioetl.domain.value_objects.run_context import RunContext


pytestmark = pytest.mark.unit


def _make_run_context() -> RunContext:
    return RunContext.create(
        run_id=deterministic_run_uuid_from_callsite(
            "test_metadata_lineage_node_builders"
        ),
        run_type=RunType.INCREMENTAL,
        started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
        provider="chembl",
        entity="activity",
    )


def _make_source_metadata() -> SourceMetadata:
    return SourceMetadata(
        type="api",
        url="https://www.ebi.ac.uk/chembl/api/data/activity",
        api_version="v1",
        input_snapshots=[
            InputSnapshotRef(
                snapshot_id="chembl-activity-batch-001",
                content_hash="a" * 64,
                immutable_uri="snapshots/chembl/activity/batch-001.jsonl.zst",
                query_fingerprint="f" * 64,
            )
        ],
    )


def test_source_system_node_exposes_snapshot_count() -> None:
    node = source_system_node(
        run_context=_make_run_context(),
        source_metadata=_make_source_metadata(),
    )

    assert node.attributes["input_snapshot_count"] == 1


def test_source_request_node_exposes_snapshot_identity() -> None:
    source_metadata = _make_source_metadata()
    node = source_request_node(
        run_context=_make_run_context(),
        input_data=BronzeMetadataInput(
            batch_id=deterministic_batch_uuid_from_callsite(
                "test_metadata_lineage_node_builders"
            ),
            record_count=10,
            compressed_size=512,
            output_path="v1/chembl/activity/2026-04-09/batch.jsonl.zst",
            started_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            completed_at=datetime(2026, 1, 1, 12, 0, tzinfo=UTC),
            source_metadata=source_metadata,
            query_string="assay_type=B",
        ),
    )

    assert node is not None
    assert node.attributes["input_snapshot_count"] == 1
    assert node.attributes["input_snapshot_ids"] == ["chembl-activity-batch-001"]
    assert node.attributes["input_snapshot_content_hashes"] == ["a" * 64]


def test_fragment_timestamp_falls_back_to_sanctioned_time_helper(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixed_now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
    monkeypatch.setattr(
        "bioetl.application.services.lineage.metadata_lineage_node_builders.current_utc_time",
        lambda: fixed_now,
    )

    assert fragment_timestamp(None, None) == fixed_now
