"""Core run-ledger lifecycle and policy event helpers."""

from __future__ import annotations

from typing import Protocol

from bioetl.application.services.control_plane.ledger.diagnostic_support import (
    sync_manifest_contract_defaults,
    sync_manifest_runtime_defaults,
)
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.control_plane.run_ledger import (
    ARTIFACT_PUBLISHED_EVENT,
    DQ_POLICY_APPLIED_EVENT,
    MANIFEST_CREATED_EVENT,
)
from bioetl.domain.types import RunID
from bioetl.domain.types.dq_contracts import DQDisposition

__all__ = [
    "record_artifact_published",
    "record_dq_policy_applied",
    "record_manifest_created",
]


class _RunLedgerCoreEventAppender(Protocol):
    @property
    def manifest_id(self) -> str: ...

    @property
    def run_id(self) -> RunID: ...

    def _append(
        self,
        *,
        event_type: str,
        status: str | None,
        stage: str | None = None,
        dataset_ref: str | None = None,
        lineage_fragment_id: str | None = None,
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry: ...


def _required_text(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} is required")
    return stripped


def record_manifest_created(
    appender: _RunLedgerCoreEventAppender,
    manifest: RunManifest,
) -> RunLedgerEntry:
    """Record manifest creation as the first control-plane event."""
    if appender.manifest_id != manifest.manifest_id:
        raise ValueError(
            "RunLedgerService manifest_id must match the persisted manifest "
            "before recording ledger events"
        )
    if appender.run_id != manifest.run_id:
        raise ValueError(
            "RunLedgerService run_id must match the persisted manifest before "
            "recording ledger events"
        )
    # Keep the first event diagnostics stable around runtime anchors.
    sync_manifest_runtime_defaults(appender, manifest)
    entry = appender._append(
        event_type=MANIFEST_CREATED_EVENT,
        status="created",
        details={
            "execution_fingerprint": manifest.execution_fingerprint,
            "pipeline_name": manifest.pipeline_name,
            "provider": manifest.provider,
            "entity": manifest.entity,
        },
    )
    # Contract/DQ anchors are still needed for subsequent lifecycle events.
    sync_manifest_contract_defaults(appender, manifest)
    return entry


def record_artifact_published(
    appender: _RunLedgerCoreEventAppender,
    *,
    layer: str,
    artifact_path: str,
    artifact_content_hash: str,
    dataset_ref: str | None = None,
    lineage_fragment_id: str | None = None,
    details: dict[str, object] | None = None,
) -> RunLedgerEntry:
    """Record a published layer artifact tied to this manifest."""
    if dataset_ref is None and lineage_fragment_id is None:
        raise ValueError(
            "Artifact publication requires dataset_ref or lineage_fragment_id"
        )
    payload: dict[str, object] = {
        "artifact_path": artifact_path,
        "artifact_content_hash": _required_text(
            artifact_content_hash, "artifact_content_hash"
        ),
    }
    if details:
        payload.update(details)
    return appender._append(
        event_type=ARTIFACT_PUBLISHED_EVENT,
        status="published",
        stage=layer,
        dataset_ref=dataset_ref,
        lineage_fragment_id=lineage_fragment_id,
        details=payload,
    )


def record_dq_policy_applied(
    appender: _RunLedgerCoreEventAppender,
    *,
    stage: str,
    status: str = "failed",
    rule_id: str | None = None,
    disposition: DQDisposition | str | None = None,
    dq_report_path: str | None = None,
    details: dict[str, object] | None = None,
) -> RunLedgerEntry:
    """Record a DQ policy outcome with stable trace anchors."""
    payload: dict[str, object] = {}
    if rule_id is not None:
        payload["rule_id"] = rule_id
    if disposition is not None:
        payload["disposition"] = str(disposition)
    if dq_report_path is not None:
        payload["dq_report_path"] = dq_report_path
    if details:
        payload.update(details)
    return appender._append(
        event_type=DQ_POLICY_APPLIED_EVENT,
        status=status,
        stage=stage,
        details=payload,
    )
