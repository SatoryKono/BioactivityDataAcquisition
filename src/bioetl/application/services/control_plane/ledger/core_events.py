"""Core run-ledger lifecycle and policy event helpers."""

from __future__ import annotations

from typing import Protocol

from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.control_plane.run_ledger import (
    ARTIFACT_PUBLISHED_EVENT,
    DQ_POLICY_APPLIED_EVENT,
    MANIFEST_CREATED_EVENT,
)
from bioetl.domain.normalization import (
    normalize_contract_ref,
    normalize_contract_version,
    normalize_control_plane_opaque_hash_ref,
)
from bioetl.domain.types import RunID
from bioetl.domain.types.dq_contracts import DQDisposition

__all__ = [
    "record_artifact_published",
    "record_dq_policy_applied",
    "record_manifest_created",
]


class _RunLedgerCorrelationFields(Protocol):
    pipeline_name: str | None
    provider: str | None
    entity: str | None
    run_type: str | None
    resolved_config_hash: str | None
    effective_config_hash: str | None
    contract_ref: str | None
    contract_version: str | None
    dq_policy_ref: str | None
    rule_bundle_version: str | None
    dq_contract_compatibility_hash: str | None
    effective_config_artifact_id: str | None


class _RunLedgerCoreEventAppender(_RunLedgerCorrelationFields, Protocol):
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
        message: str | None = None,
        error_type: str | None = None,
        dataset_ref: str | None = None,
        lineage_fragment_id: str | None = None,
        metrics_snapshot: dict[str, int] | None = None,
        details: dict[str, object] | None = None,
    ) -> RunLedgerEntry: ...


def _required_text(value: str, field_name: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValueError(f"{field_name} is required")
    return stripped


def _coalesce_missing(current: str | None, default: str | None) -> str | None:
    """Return default only when current value is missing."""
    if current is None:
        return default
    return current


def sync_manifest_runtime_defaults(
    host: _RunLedgerCoreEventAppender,
    manifest: RunManifest,
) -> None:
    """Hydrate runtime correlation defaults from the immutable manifest."""
    code_provenance = manifest.code_provenance
    host.pipeline_name = _coalesce_missing(host.pipeline_name, manifest.pipeline_name)
    host.provider = _coalesce_missing(host.provider, manifest.provider)
    host.entity = _coalesce_missing(host.entity, manifest.entity)
    host.run_type = _coalesce_missing(host.run_type, manifest.run_type.value)
    host.resolved_config_hash = _coalesce_missing(
        host.resolved_config_hash,
        normalize_control_plane_opaque_hash_ref(code_provenance.resolved_config_hash),
    )
    host.effective_config_hash = _coalesce_missing(
        host.effective_config_hash,
        normalize_control_plane_opaque_hash_ref(code_provenance.effective_config_hash),
    )


def sync_manifest_contract_defaults(
    host: _RunLedgerCoreEventAppender,
    manifest: RunManifest,
) -> None:
    """Hydrate contract/DQ correlation defaults from the immutable manifest."""
    code_provenance = manifest.code_provenance
    host.contract_ref = _coalesce_missing(
        host.contract_ref,
        normalize_contract_ref(code_provenance.contract_ref),
    )
    host.contract_version = _coalesce_missing(
        host.contract_version,
        normalize_contract_version(code_provenance.contract_version),
    )
    host.dq_policy_ref = _coalesce_missing(
        host.dq_policy_ref,
        code_provenance.dq_policy_ref,
    )
    host.rule_bundle_version = _coalesce_missing(
        host.rule_bundle_version,
        code_provenance.rule_bundle_version,
    )
    host.dq_contract_compatibility_hash = _coalesce_missing(
        host.dq_contract_compatibility_hash,
        code_provenance.dq_contract_compatibility_hash,
    )
    host.effective_config_artifact_id = _coalesce_missing(
        host.effective_config_artifact_id,
        code_provenance.effective_config_artifact_id,
    )


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
        "artifact_path": _required_text(artifact_path, "artifact_path"),
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
