"""Ledger artifact and input-snapshot recording rules (#11250)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, TypedDict, cast

from bioetl.application.services.control_plane.ledger.input_snapshot_recording import (
    record_input_snapshots_from_artifact,
)
from bioetl.domain.control_plane import RunLedgerEntry

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.ledger.service import (
        RunLedgerService,
    )

__all__ = [
    "ArtifactPublicationRequest",
    "canonical_lineage_fragment_id",
    "record_input_snapshots_from_artifact",
    "record_published_artifact",
]


@dataclass(frozen=True, slots=True)
class ArtifactPublicationRequest:
    """Immutable command for one artifact-publication ledger event."""

    layer: str
    artifact_path: str
    artifact_content_hash: str
    dataset_ref: str | None = None
    lineage_fragment_id: str | None = None
    details: dict[str, object] | None = None

    @classmethod
    def from_artifact_details(
        cls,
        *,
        layer: str,
        artifact_path: str,
        details: dict[str, object] | None,
    ) -> ArtifactPublicationRequest:
        """Build a publication command from a storage artifact payload."""
        details_payload = details or {}
        raw_dataset_ref = details_payload.get("dataset_ref")
        return cls(
            layer=layer,
            artifact_path=artifact_path,
            artifact_content_hash=str(
                details_payload.get("artifact_content_hash")
                or details_payload.get("content_hash")
                or ""
            ),
            dataset_ref=None if raw_dataset_ref is None else str(raw_dataset_ref),
            lineage_fragment_id=canonical_lineage_fragment_id(
                details_payload.get("lineage_fragment_id")
            ),
            details=details,
        )

    def record(self, target: object) -> RunLedgerEntry:
        """Record through a concrete appender or a compatible public service."""
        kwargs = _ArtifactPublicationKwargs(
            layer=self.layer,
            artifact_path=self.artifact_path,
            artifact_content_hash=self.artifact_content_hash,
            dataset_ref=self.dataset_ref,
            lineage_fragment_id=self.lineage_fragment_id,
            details=self.details,
        )
        recorder = cast("_ArtifactPublicationRecorder", target)
        return recorder.record_artifact_published(**kwargs)


def canonical_lineage_fragment_id(raw: object) -> str | None:
    """Reject layer aliases such as ``bronze`` as fragment identifiers."""
    if raw is None:
        return None
    value = str(raw).strip()
    if not value or value.lower() in {"bronze", "silver", "gold"}:
        return None
    return value


class _ArtifactPublicationKwargs(TypedDict):
    layer: str
    artifact_path: str
    artifact_content_hash: str
    dataset_ref: str | None
    lineage_fragment_id: str | None
    details: dict[str, object] | None


class _ArtifactPublicationRecorder(Protocol):
    def record_artifact_published(
        self,
        *,
        layer: str,
        artifact_path: str,
        artifact_content_hash: str,
        dataset_ref: str | None = None,
        lineage_fragment_id: str | None = None,
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry: ...


def record_published_artifact(
    service: RunLedgerService,
    *,
    layer: str,
    artifact_path: str,
    details: dict[str, object] | None,
) -> object:
    """Record one published artifact and any Bronze input snapshots."""
    request = ArtifactPublicationRequest.from_artifact_details(
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
