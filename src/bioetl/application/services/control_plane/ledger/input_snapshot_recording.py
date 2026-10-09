"""Bronze input-snapshot recording rules (#11250)."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, TypedDict

from bioetl.application.services.control_plane.ledger._input_snapshot_manifest import (
    persist_input_snapshots_on_manifest,
)
from bioetl.domain.control_plane import RunInputSnapshotRef

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )


class _SnapshotPublishKwargs(TypedDict):
    """Publish kwargs for one validated input-snapshot payload."""

    provider: str
    entity: str
    pipeline_name: str
    snapshot_id: str
    content_hash: str
    immutable_uri: str
    bronze_batch_ref: str
    query_fingerprint: str | None
    details: Mapping[str, object]


def _published_snapshot_kwargs(
    snapshot: dict[str, object],
    *,
    details: dict[str, object],
    artifact_path: str,
    snapshot_id: str,
) -> _SnapshotPublishKwargs:
    """Build publish kwargs for one validated snapshot payload."""
    return {
        "provider": str(details.get("provider") or ""),
        "entity": str(details.get("entity") or ""),
        "pipeline_name": str(details.get("pipeline_name") or ""),
        "snapshot_id": snapshot_id,
        "content_hash": str(snapshot.get("content_hash") or ""),
        "immutable_uri": str(snapshot.get("immutable_uri")),
        "bronze_batch_ref": artifact_path,
        "query_fingerprint": (
            None
            if snapshot.get("query_fingerprint") is None
            else str(snapshot.get("query_fingerprint"))
        ),
        "details": {
            key: value
            for key, value in snapshot.items()
            if key not in {"snapshot_id", "content_hash", "immutable_uri"}
        },
    }


def _record_one_input_snapshot(
    service: RunLedgerService,
    *,
    snapshot: object,
    details: dict[str, object],
    artifact_path: str,
) -> RunInputSnapshotRef | None:
    """Validate, publish and project one snapshot payload; None skips noise."""
    if not isinstance(snapshot, dict):
        return None
    if snapshot.get("immutable_uri") is None:
        return None
    snapshot_id = str(snapshot.get("snapshot_id") or "").strip()
    if not snapshot_id:
        raise ValueError("input snapshot is missing snapshot_id")
    service.record_input_snapshot_published(
        **_published_snapshot_kwargs(
            snapshot,
            details=details,
            artifact_path=artifact_path,
            snapshot_id=snapshot_id,
        )
    )
    return _snapshot_ref_from_payload(snapshot, snapshot_id=snapshot_id)


def record_input_snapshots_from_artifact(
    service: RunLedgerService,
    *,
    layer: str,
    artifact_path: str,
    details: dict[str, object] | None,
) -> None:
    """Record immutable input snapshots published with Bronze metadata."""
    if layer != "bronze" or not details:
        return
    raw_snapshots = details.get("input_snapshots")
    if not isinstance(raw_snapshots, list):
        return
    attached: list[RunInputSnapshotRef] = []
    for snapshot in raw_snapshots:
        ref = _record_one_input_snapshot(
            service,
            snapshot=snapshot,
            details=details,
            artifact_path=artifact_path,
        )
        if ref is not None:
            attached.append(ref)
    persist_input_snapshots_on_manifest(
        service,
        snapshots=tuple(attached),
        provider=str(details.get("provider") or ""),
        entity=str(details.get("entity") or ""),
        pipeline_name=str(details.get("pipeline_name") or ""),
        input_snapshot_verified=_local_batch_file_verified(artifact_path),
    )


def _local_batch_file_verified(artifact_path: str) -> bool | None:
    """Return True only when a local batch file demonstrably exists (#11711).

    Non-local references stay unset so readers report object_not_verified
    instead of assuming presence from a recorded hash.
    """
    raw = str(artifact_path or "").strip()
    if "://" in raw:
        if not raw.lower().startswith("file://"):
            return None
        raw = raw[7:]
    if not raw:
        return None
    return True if Path(raw).is_file() else None


def _snapshot_ref_from_payload(
    payload: dict[str, object],
    *,
    snapshot_id: str,
) -> RunInputSnapshotRef:
    return RunInputSnapshotRef(
        snapshot_id=snapshot_id,
        content_hash=str(payload.get("content_hash") or ""),
        immutable_uri=(
            None
            if payload.get("immutable_uri") is None
            else str(payload.get("immutable_uri"))
        ),
        query_fingerprint=(
            None
            if payload.get("query_fingerprint") is None
            else str(payload.get("query_fingerprint"))
        ),
        storage_provider=(
            None
            if payload.get("storage_provider") is None
            else str(payload.get("storage_provider"))
        ),
        object_bucket=(
            None
            if payload.get("object_bucket") is None
            else str(payload.get("object_bucket"))
        ),
        object_key=(
            None
            if payload.get("object_key") is None
            else str(payload.get("object_key"))
        ),
        object_version_id=(
            None
            if payload.get("object_version_id") is None
            else str(payload.get("object_version_id"))
        ),
        etag=None if payload.get("etag") is None else str(payload.get("etag")),
        last_modified=_optional_iso_text(payload.get("last_modified")),
        captured_at=_optional_datetime(payload.get("captured_at")),
    )


def _optional_datetime(value: object) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    token = str(value).strip()
    if not token:
        return None
    return datetime.fromisoformat(token.replace("Z", "+00:00"))


def _optional_iso_text(value: object) -> str | None:
    moment = _optional_datetime(value)
    return None if moment is None else moment.isoformat()
