"""Ledger artifact and input-snapshot recording rules (#11250)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.ledger.input_snapshot_recording import (
    record_input_snapshots_from_artifact,
)

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )

__all__ = [
    "canonical_lineage_fragment_id",
    "record_input_snapshots_from_artifact",
    "record_published_artifact",
]


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
