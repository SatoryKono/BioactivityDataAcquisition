"""Ledger artifact and input-snapshot recording rules (#11250)."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import TYPE_CHECKING

from bioetl.domain.control_plane import RunInputSnapshotRef, RunSourceRef
from bioetl.domain.control_plane.reproducibility_policy import resolve_replay_capability

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )
    from bioetl.domain.control_plane import RunManifest


def canonical_lineage_fragment_id(raw: object) -> str | None:
    """Reject layer aliases such as ``bronze`` as fragment identifiers."""
    if raw is None:
        return None
    value = str(raw).strip()
    if not value or value.lower() in {"bronze", "silver", "gold"}:
        return None
    return value


def record_published_artifact(
    service: RunLedgerService,
    *,
    layer: str,
    artifact_path: str,
    details: dict[str, object] | None,
) -> object:
    """Record one published artifact and any Bronze input snapshots."""
    dataset_ref = None
    lineage_fragment_id = None
    if details is not None:
        raw_dataset_ref = details.get("dataset_ref")
        raw_lineage_fragment_id = details.get("lineage_fragment_id")
        dataset_ref = None if raw_dataset_ref is None else str(raw_dataset_ref)
        lineage_fragment_id = canonical_lineage_fragment_id(raw_lineage_fragment_id)
        artifact_content_hash = str(
            details.get("artifact_content_hash") or details.get("content_hash") or ""
        )
    else:
        artifact_content_hash = ""
    entry = service.record_artifact_published(
        layer=layer,
        artifact_path=artifact_path,
        artifact_content_hash=artifact_content_hash,
        dataset_ref=dataset_ref,
        lineage_fragment_id=lineage_fragment_id,
        details=details,
    )
    record_input_snapshots_from_artifact(
        service,
        layer=layer,
        artifact_path=artifact_path,
        details=details,
    )
    return entry


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
        if not isinstance(snapshot, dict):
            continue
        immutable_uri = snapshot.get("immutable_uri")
        if immutable_uri is None:
            continue
        snapshot_id = str(snapshot.get("snapshot_id") or "").strip()
        if not snapshot_id:
            raise ValueError("input snapshot is missing snapshot_id")
        service.record_input_snapshot_published(
            provider=str(details.get("provider") or ""),
            entity=str(details.get("entity") or ""),
            pipeline_name=str(details.get("pipeline_name") or ""),
            snapshot_id=snapshot_id,
            content_hash=str(snapshot.get("content_hash") or ""),
            immutable_uri=str(immutable_uri),
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
        attached.append(_snapshot_ref_from_payload(snapshot, snapshot_id=snapshot_id))
    persist_input_snapshots_on_manifest(
        service,
        snapshots=tuple(attached),
        provider=str(details.get("provider") or ""),
        entity=str(details.get("entity") or ""),
        pipeline_name=str(details.get("pipeline_name") or ""),
    )


def persist_input_snapshots_on_manifest(
    service: RunLedgerService,
    *,
    snapshots: tuple[RunInputSnapshotRef, ...],
    provider: str,
    entity: str,
    pipeline_name: str,
) -> RunManifest | None:
    """Copy Bronze snapshots onto the persisted manifest and recompute capability."""
    if not snapshots:
        return None
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
    resume_requested = False
    launch_context = getattr(manifest, "launch_context", None)
    if isinstance(launch_context, dict):
        resume_requested = bool(launch_context.get("resume"))
    new_refs = _merge_source_refs(
        getattr(manifest, "source_refs", ()) or (),
        snapshots,
        provider=provider or str(getattr(manifest, "provider", "") or ""),
        entity=entity or str(getattr(manifest, "entity", "") or ""),
        pipeline_name=pipeline_name
        or str(getattr(manifest, "pipeline_name", "") or ""),
    )
    capability = resolve_replay_capability(
        source_refs=new_refs,
        resume_requested=resume_requested,
    )
    updated = replace(
        manifest,
        source_refs=new_refs,
        replay_capability=capability,
    )
    saver(updated)
    return updated


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
        if not attached and (
            (not provider or ref.provider == provider)
            and (not entity or ref.entity == entity)
        ):
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
        last_modified=_optional_datetime(payload.get("last_modified")),
        captured_at=_optional_datetime(payload.get("captured_at")),
    )


def _optional_datetime(value: object) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    token = str(value).strip()
    if not token:
        return None
    return datetime.fromisoformat(token.replace("Z", "+00:00"))
