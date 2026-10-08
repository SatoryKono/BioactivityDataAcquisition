"""Ledger artifact and input-snapshot recording rules (#11250)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.services.control_plane.ledger import core_events as _core_events
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
    return _core_events.canonical_lineage_fragment_id(raw)


def record_published_artifact(
    service: RunLedgerService,
    *,
    layer: str,
    artifact_path: str,
    details: dict[str, object] | None,
) -> object:
    """Record one published artifact and any Bronze input snapshots."""
    request = _core_events.ArtifactPublicationRequest.from_artifact_details(
        layer=layer,
        artifact_path=artifact_path,
        details=details,
    )
    entry = request.record(service)
    record_input_snapshots_from_artifact(
        service,
        layer=layer,
        artifact_path=artifact_path,
        details=details,
    )
    return entry
