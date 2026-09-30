"""Bronze input-snapshot recording rules (#11250)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from bioetl.domain.control_plane import RunInputSnapshotRef, RunSourceRef
from bioetl.domain.control_plane.reproducibility_policy import resolve_replay_capability

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )
    from bioetl.domain.control_plane import RunManifest


def _published_snapshot_kwargs(
    snapshot: dict[str, object],
    *,
    details: dict[str, object],
    artifact_path: str,
    snapshot_id: str,
) -> dict[str, Any]:
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


def _load_manifest_for_persist(
    service: RunLedgerService,
) -> tuple[Any, RunManifest] | None:
    """Return the manifest saver and manifest when the ledger can persist."""
    port = getattr(service, "manifest_port", None)
    manifest_id = str(getattr(service, "manifest_id", "") or "").strip()
    if port is None or not manifest_id or manifest_id == "pending":
        return None
    getter = getattr(port, "get", None)
    saver = getattr(port, "save", None)
    if not callable(getter) or not callable(saver):
        return None
    manifest = getter(manifest_id)
    if manifest is None:
        return None
    return saver, cast("RunManifest", manifest)


def _manifest_text(manifest: RunManifest, name: str, override: str) -> str:
    """Prefer an explicit override, else the manifest text field."""
    if override:
        return override
    return str(getattr(manifest, name, "") or "")


def _resume_requested(manifest: RunManifest) -> bool:
    """Return whether the manifest launch context requested resume."""
    launch_context = getattr(manifest, "launch_context", None)
    if not isinstance(launch_context, dict):
        return False
    return bool(launch_context.get("resume"))


def _with_verified_snapshot_fingerprint(updated: RunManifest) -> RunManifest:
    """Stamp the recorded input-snapshot fingerprint on one manifest."""
    recorded = dict(getattr(updated, "objects", None) or {})
    recorded["input_snapshot_fingerprint"] = True
    return replace(updated, objects=recorded)


def persist_input_snapshots_on_manifest(
    service: RunLedgerService,
    *,
    snapshots: tuple[RunInputSnapshotRef, ...],
    provider: str,
    entity: str,
    pipeline_name: str,
    input_snapshot_verified: bool | None = None,
) -> RunManifest | None:
    """Copy Bronze snapshots onto the persisted manifest and recompute capability."""
    if not snapshots:
        return None
    loaded = _load_manifest_for_persist(service)
    if loaded is None:
        return None
    saver, manifest = loaded
    new_refs = _merge_source_refs(
        getattr(manifest, "source_refs", ()) or (),
        snapshots,
        provider=_manifest_text(manifest, "provider", provider),
        entity=_manifest_text(manifest, "entity", entity),
        pipeline_name=_manifest_text(manifest, "pipeline_name", pipeline_name),
    )
    capability = resolve_replay_capability(
        source_refs=new_refs,
        resume_requested=_resume_requested(manifest),
    )
    updated = replace(
        manifest,
        source_refs=new_refs,
        replay_capability=capability,
    )
    if input_snapshot_verified is True:
        updated = _with_verified_snapshot_fingerprint(updated)
    saver(updated)
    return updated


def _ref_matches_owner(
    ref: RunSourceRef,
    *,
    provider: str,
    entity: str,
) -> bool:
    """Return whether one source ref belongs to the snapshot owner."""
    return (not provider or ref.provider == provider) and (
        not entity or ref.entity == entity
    )


def _merge_source_refs(
    source_refs: tuple[RunSourceRef, ...],
    snapshots: tuple[RunInputSnapshotRef, ...],
    *,
    provider: str,
    entity: str,
    pipeline_name: str,
) -> tuple[RunSourceRef, ...]:
    if not source_refs:
        return (
            RunSourceRef(
                provider=provider or "unknown",
                entity=entity or "unknown",
                pipeline_name=pipeline_name or "unknown_pipeline",
                input_snapshots=snapshots,
            ),
        )
    merged: list[RunSourceRef] = []
    attached = False
    for ref in source_refs:
        if not attached and _ref_matches_owner(ref, provider=provider, entity=entity):
            merged.append(
                replace(
                    ref,
                    input_snapshots=_dedupe_snapshots(ref.input_snapshots, snapshots),
                )
            )
            attached = True
        else:
            merged.append(ref)
    if not attached:
        first = source_refs[0]
        merged[0] = replace(
            first,
            input_snapshots=_dedupe_snapshots(first.input_snapshots, snapshots),
        )
    return tuple(merged)


def _dedupe_snapshots(
    existing: tuple[RunInputSnapshotRef, ...],
    incoming: tuple[RunInputSnapshotRef, ...],
) -> tuple[RunInputSnapshotRef, ...]:
    seen = {item.snapshot_id for item in existing}
    extra = tuple(item for item in incoming if item.snapshot_id not in seen)
    return existing + extra


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
