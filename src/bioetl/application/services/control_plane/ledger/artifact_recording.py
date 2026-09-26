"""Ledger artifact and input-snapshot recording rules (#11250)."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )


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
