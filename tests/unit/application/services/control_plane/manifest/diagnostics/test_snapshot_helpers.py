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
"""Coverage for input-snapshot manifest diagnostics helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pytest

from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_ledger import (
    collect_ledger_input_snapshot_refs,
)
from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_materialization import (
    resolve_post_manifest_input_snapshot_materialization_mode,
)
from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_refs import (
    collect_input_snapshot_content_hashes,
    collect_input_snapshot_ids,
    collect_input_snapshot_refs,
    compute_input_snapshot_identity_fingerprint,
)
from bioetl.application.services.control_plane.manifest.diagnostics.snapshot_summary import (
    merge_ledger_input_snapshots_into_summary,
)
from bioetl.application.services.control_plane.replay.historical_certification import (
    LIVE_CAPTURE_SNAPSHOT_MATERIALIZED,
    MIXED_POST_MANIFEST_SNAPSHOT_MATERIALIZATION,
)
from bioetl.domain.control_plane import (
    RunInputSnapshotRef,
    RunLedgerEntry,
    RunManifest,
    RunSourceRef,
)
from bioetl.domain.control_plane.run_ledger import INPUT_SNAPSHOT_PUBLISHED_EVENT
from bioetl.domain.types import RunID


pytestmark = pytest.mark.unit


def _run_id() -> RunID:
    return RunID(UUID("00000000-0000-0000-0000-000000000123"))


def _ledger_entry(
    entry_id: str,
    *,
    snapshot_id: str = "snap-1",
    content_hash: str = "sha256:abc",
    immutable_uri: str = "file:///bronze/snap-1",
    materialization_mode: str | None = None,
) -> RunLedgerEntry:
    return RunLedgerEntry(
        entry_id=entry_id,
        manifest_id="manifest-1",
        run_id=_run_id(),
        event_type=INPUT_SNAPSHOT_PUBLISHED_EVENT,
        occurred_at=datetime(2026, 6, 16, tzinfo=UTC),
        details={
            "provider": "chembl",
            "entity": "target",
            "pipeline_name": "chembl_target",
            "query": "limit=1",
            "snapshot_id": snapshot_id,
            "content_hash": content_hash,
            "immutable_uri": immutable_uri,
            "materialization_mode": materialization_mode,
        },
    )


def test_collect_ledger_input_snapshot_refs_filters_invalid_and_dedupes() -> None:
    valid = _ledger_entry("entry-b", snapshot_id="snap-b")
    replacement = _ledger_entry(
        "entry-a", snapshot_id="snap-b", content_hash="sha256:new"
    )
    missing_required = _ledger_entry("entry-c", immutable_uri=" ")
    unrelated = RunLedgerEntry(
        entry_id="entry-d",
        manifest_id="manifest-1",
        run_id=_run_id(),
        event_type="run_finished",
        occurred_at=datetime(2026, 6, 16, tzinfo=UTC),
        details={"snapshot_id": "ignored"},
    )

    refs = collect_ledger_input_snapshot_refs(
        (valid, missing_required, unrelated, replacement)
    )

    assert refs == [
        {
            "provider": "chembl",
            "entity": "target",
            "pipeline_name": "chembl_target",
            "query": "limit=1",
            "snapshot_id": "snap-b",
            "content_hash": "sha256:new",
            "immutable_uri": "file:///bronze/snap-1",
            "query_fingerprint": None,
            "storage_provider": None,
            "object_bucket": None,
            "object_key": None,
            "object_version_id": None,
            "etag": None,
            "last_modified": None,
            "captured_at": None,
            "materialization_mode": LIVE_CAPTURE_SNAPSHOT_MATERIALIZED,
            "certification_scope": None,
            "certification_basis": None,
            "certification_artifact_ref": None,
            "upstream_run_id": None,
            "upstream_manifest_id": None,
            "source_event_id": "entry-a",
        }
    ]


def test_materialization_mode_summary_handles_empty_single_and_mixed_modes() -> None:
    assert resolve_post_manifest_input_snapshot_materialization_mode([]) is None
    assert (
        resolve_post_manifest_input_snapshot_materialization_mode(
            [{"materialization_mode": " live_capture_snapshot_materialized "}]
        )
        == LIVE_CAPTURE_SNAPSHOT_MATERIALIZED
    )
    assert (
        resolve_post_manifest_input_snapshot_materialization_mode(
            [
                {"materialization_mode": LIVE_CAPTURE_SNAPSHOT_MATERIALIZED},
                {"materialization_mode": "historical_source_snapshot_certified"},
            ]
        )
        == MIXED_POST_MANIFEST_SNAPSHOT_MATERIALIZATION
    )


def test_manifest_snapshot_refs_and_identity_fingerprint_are_deterministic() -> None:
    manifest = RunManifest(
        manifest_id="manifest-1",
        execution_fingerprint="fingerprint-1",
        pipeline_name="chembl_target",
        provider="chembl",
        entity="target",
        run_id=_run_id(),
        source_refs=(
            RunSourceRef(
                provider="chembl",
                entity="target",
                pipeline_name="chembl_target",
                query="limit=1",
                input_snapshots=(
                    RunInputSnapshotRef(
                        snapshot_id="snap-1",
                        content_hash="sha256:abc",
                        immutable_uri="file:///bronze/snap-1",
                    ),
                ),
            ),
        ),
    )

    refs = collect_input_snapshot_refs(manifest)

    assert collect_input_snapshot_ids(refs) == ["snap-1"]
    assert collect_input_snapshot_content_hashes(refs) == ["sha256:abc"]
    assert compute_input_snapshot_identity_fingerprint(refs)


def test_merge_ledger_input_snapshots_into_summary_updates_snapshot_fields() -> None:
    summary = {
        "input_snapshots": [
            {"snapshot_id": "snap-a", "content_hash": "sha256:old"},
        ],
        "source_posture": "live_or_unknown_inputs",
        "snapshot_status": "none",
    }

    merged = merge_ledger_input_snapshots_into_summary(
        summary,
        (
            _ledger_entry("entry-b", snapshot_id="snap-b", content_hash="sha256:b"),
            _ledger_entry("entry-a", snapshot_id="snap-a", content_hash="sha256:a"),
        ),
    )

    assert summary["input_snapshots"] == [
        {"snapshot_id": "snap-a", "content_hash": "sha256:old"}
    ]
    assert merged["input_snapshot_count"] == 2
    assert merged["input_snapshot_ids"] == ["snap-a", "snap-b"]
    assert merged["input_snapshot_content_hashes"] == ["sha256:a", "sha256:b"]
    assert merged["input_snapshot_identity_fingerprint"]
    assert merged["source_posture"] == LIVE_CAPTURE_SNAPSHOT_MATERIALIZED
    assert merged["snapshot_status"] == "ledger_derived"


def test_merge_ledger_input_snapshots_returns_original_when_no_ledger_refs() -> None:
    summary = {"input_snapshots": []}

    assert merge_ledger_input_snapshots_into_summary(summary, ()) is summary
