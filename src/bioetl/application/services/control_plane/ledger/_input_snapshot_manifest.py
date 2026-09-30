"""Manifest persistence for Bronze input snapshots (#11250)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from typing import TYPE_CHECKING, cast

from bioetl.domain.control_plane import RunInputSnapshotRef, RunSourceRef
from bioetl.domain.control_plane.reproducibility_policy import resolve_replay_capability

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )
    from bioetl.domain.control_plane import RunManifest


def _load_manifest_for_persist(
    service: RunLedgerService,
) -> tuple[Callable[[RunManifest], None], RunManifest] | None:
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
