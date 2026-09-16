"""Diagnostic/default helpers owned by the run-ledger package."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.normalization import (
    normalize_contract_ref,
    normalize_contract_version,
    normalize_control_plane_opaque_hash_ref,
)
from bioetl.domain.types import RunID

if TYPE_CHECKING:
    from bioetl.domain.control_plane import RunManifest

LEDGER_DIAGNOSTIC_CONTRACT_VERSION = "v1"


class RunLedgerCorrelationFieldsProtocol(Protocol):
    """Shared correlation defaults carried by ledger services and diagnostics."""

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


class _RunLedgerDefaultsHost(RunLedgerCorrelationFieldsProtocol, Protocol):
    """Structural host for manifest-derived ledger correlation defaults."""


@dataclass(frozen=True, slots=True)
class _RunLedgerDiagnosticRequest:
    event_type: str
    event_family: str
    manifest_id: str
    run_id: RunID
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
    composite_run_id: str | None
    status: str | None
    stage: str | None
    error_type: str | None
    dataset_ref: str | None
    lineage_fragment_id: str | None
    details: dict[str, object] | None


def build_run_ledger_diagnostic_request(
    service: RunLedgerCorrelationFieldsProtocol,
    *,
    event_type: str,
    event_family: str,
    manifest_id: str,
    run_id: RunID,
    composite_run_id: str | None,
    status: str | None,
    stage: str | None,
    error_type: str | None,
    dataset_ref: str | None,
    lineage_fragment_id: str | None,
    details: dict[str, object] | None,
) -> _RunLedgerDiagnosticRequest:
    """Build one diagnostic request from shared ledger correlation defaults."""
    return _RunLedgerDiagnosticRequest(
        event_type=event_type,
        event_family=event_family,
        manifest_id=manifest_id,
        run_id=run_id,
        pipeline_name=service.pipeline_name,
        provider=service.provider,
        entity=service.entity,
        run_type=service.run_type,
        resolved_config_hash=service.resolved_config_hash,
        effective_config_hash=service.effective_config_hash,
        contract_ref=service.contract_ref,
        contract_version=service.contract_version,
        dq_policy_ref=service.dq_policy_ref,
        rule_bundle_version=service.rule_bundle_version,
        dq_contract_compatibility_hash=service.dq_contract_compatibility_hash,
        effective_config_artifact_id=service.effective_config_artifact_id,
        composite_run_id=composite_run_id,
        status=status,
        stage=stage,
        error_type=error_type,
        dataset_ref=dataset_ref,
        lineage_fragment_id=lineage_fragment_id,
        details=details,
    )


def _coalesce_missing(current: str | None, default: str | None) -> str | None:
    """Return default only when current value is missing."""
    if current is None:
        return default
    return current


def sync_manifest_runtime_defaults(
    host: _RunLedgerDefaultsHost,
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
    host: _RunLedgerDefaultsHost,
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
