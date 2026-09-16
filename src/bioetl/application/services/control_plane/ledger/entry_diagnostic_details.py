"""Diagnostic detail payload builders for append-only run-ledger events."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from bioetl.domain.normalization import (
    normalize_contract_ref,
    normalize_contract_version,
    normalize_control_plane_opaque_hash_ref,
)
from bioetl.domain.types import RunID

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


def _apply_optional_diagnostic_anchor(
    diagnostic: dict[str, object],
    field_name: str,
    value: str | None,
) -> None:
    """Attach one non-empty correlation anchor to diagnostic payload."""
    if value is not None and value.strip():
        diagnostic[field_name] = value


def build_run_ledger_diagnostic_details(
    request: _RunLedgerDiagnosticRequest,
) -> dict[str, object]:
    """Attach stable diagnostic metadata contract for ledger tooling."""
    normalized_details: dict[str, object] = dict(request.details or {})

    diagnostic: dict[str, object] = {
        "diagnostic_contract_version": LEDGER_DIAGNOSTIC_CONTRACT_VERSION,
        "event_type": request.event_type,
        "event_family": request.event_family,
        "manifest_id": request.manifest_id,
        "run_id": str(request.run_id),
    }
    effective_config_hash = normalize_control_plane_opaque_hash_ref(
        request.effective_config_hash
    )
    resolved_config_hash = normalize_control_plane_opaque_hash_ref(
        request.resolved_config_hash
    )
    contract_ref = normalize_contract_ref(request.contract_ref)
    contract_version = normalize_contract_version(request.contract_version)
    _apply_optional_diagnostic_anchor(diagnostic, "pipeline", request.pipeline_name)
    _apply_optional_diagnostic_anchor(diagnostic, "provider", request.provider)
    _apply_optional_diagnostic_anchor(diagnostic, "entity", request.entity)
    _apply_optional_diagnostic_anchor(diagnostic, "run_type", request.run_type)
    _apply_optional_diagnostic_anchor(
        diagnostic,
        "resolved_config_hash",
        resolved_config_hash,
    )
    _apply_optional_diagnostic_anchor(
        diagnostic,
        "effective_config_hash",
        effective_config_hash,
    )
    _apply_optional_diagnostic_anchor(diagnostic, "contract_ref", contract_ref)
    _apply_optional_diagnostic_anchor(
        diagnostic,
        "contract_version",
        contract_version,
    )
    _apply_optional_diagnostic_anchor(
        diagnostic,
        "dq_policy_ref",
        request.dq_policy_ref,
    )
    _apply_optional_diagnostic_anchor(
        diagnostic,
        "rule_bundle_version",
        request.rule_bundle_version,
    )
    _apply_optional_diagnostic_anchor(
        diagnostic,
        "dq_contract_compatibility_hash",
        request.dq_contract_compatibility_hash,
    )
    _apply_optional_diagnostic_anchor(
        diagnostic,
        "effective_config_artifact_id",
        request.effective_config_artifact_id,
    )
    _apply_optional_diagnostic_anchor(
        diagnostic,
        "composite_run_id",
        request.composite_run_id,
    )
    if request.status is not None:
        diagnostic["status"] = request.status
    if request.stage is not None:
        diagnostic["stage"] = request.stage
    if request.error_type is not None:
        diagnostic["error_type"] = request.error_type
    if request.dataset_ref is not None:
        diagnostic["dataset_ref"] = request.dataset_ref
        diagnostic["artifact_id"] = request.dataset_ref
    if request.lineage_fragment_id is not None:
        diagnostic["lineage_fragment_id"] = request.lineage_fragment_id

    normalized_details["_diagnostic"] = diagnostic
    return normalized_details


__all__ = [
    "RunLedgerCorrelationFieldsProtocol",
    "build_run_ledger_diagnostic_details",
    "build_run_ledger_diagnostic_request",
]
