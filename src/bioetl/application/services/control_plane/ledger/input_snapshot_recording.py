"""Bronze input-snapshot recording rules (#11250)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.input_snapshot_identity import (
    InputSnapshotIdentity,
)
from bioetl.application.services.control_plane.ledger._input_snapshot_manifest import (
    persist_input_snapshots_on_manifest,
)
from bioetl.domain.control_plane import RunInputSnapshotRef

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )


@dataclass(frozen=True, slots=True)
class _SnapshotPublishRequest(InputSnapshotIdentity):
    """Validated input-snapshot publication request."""

    query_fingerprint: str | None
    details: Mapping[str, object]

    def publish(self, service: RunLedgerService) -> None:
        """Append this snapshot through the ledger service port."""
        service.record_input_snapshot_published(
            provider=self.provider,
            entity=self.entity,
            pipeline_name=self.pipeline_name,
            snapshot_id=self.snapshot_id,
            content_hash=self.content_hash,
            immutable_uri=self.immutable_uri,
            bronze_batch_ref=self.bronze_batch_ref,
            query_fingerprint=self.query_fingerprint,
            details=self.details,
        )


def _published_snapshot_request(
    snapshot: dict[str, object],
    *,
    details: dict[str, object],
    artifact_path: str,
    snapshot_id: str,
) -> _SnapshotPublishRequest:
    """Build a publication request for one validated snapshot payload."""
    return _SnapshotPublishRequest(
        provider=str(details.get("provider") or ""),
        entity=str(details.get("entity") or ""),
        pipeline_name=str(details.get("pipeline_name") or ""),
        snapshot_id=snapshot_id,
        content_hash=str(snapshot.get("content_hash") or ""),
        immutable_uri=str(snapshot.get("immutable_uri")),
        bronze_batch_ref=artifact_path,
        query_fingerprint=(
            None
            if snapshot.get("query_fingerprint") is None
            else str(snapshot.get("query_fingerprint"))
        ),
        details={
            key: value
            for key, value in snapshot.items()
            if key not in {"snapshot_id", "content_hash", "immutable_uri"}
        },
    )


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
    request = _published_snapshot_request(
        snapshot,
        details=details,
        artifact_path=artifact_path,
        snapshot_id=snapshot_id,
    )
    request.publish(service)
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
