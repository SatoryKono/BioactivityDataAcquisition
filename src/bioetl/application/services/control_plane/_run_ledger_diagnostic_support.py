"""Private diagnostic/default helpers for :mod:`run_ledger_service`."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

from bioetl.domain.normalization import (
    normalize_contract_ref,
    normalize_contract_version,
    normalize_control_plane_opaque_hash_ref,
)

if TYPE_CHECKING:
    from bioetl.domain.control_plane import RunManifest
    from bioetl.domain.types import RunID

LEDGER_DIAGNOSTIC_CONTRACT_VERSION = "v1"


class _RunLedgerDefaultsHost(Protocol):
    pipeline_name: str | None
    provider: str | None
    entity: str | None
    run_type: str | None
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


def _coalesce_missing(current: str | None, default: str | None) -> str | None:
    """Return default only when current value is missing."""
    if current is None:
        return default
    return current


def _apply_optional_diagnostic_anchor(
    diagnostic: dict[str, object],
    field_name: str,
    value: str | None,
) -> None:
    """Attach one non-empty correlation anchor to diagnostic payload."""
    if value is None:
        return
    if not value.strip():
        return
    diagnostic[field_name] = value


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
    host.effective_config_hash = _coalesce_missing(
        host.effective_config_hash,
        normalize_control_plane_opaque_hash_ref(code_provenance.config_hash),
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


def build_run_ledger_diagnostic_details(
    request: _RunLedgerDiagnosticRequest,
) -> dict[str, object]:
    """Attach stable diagnostic metadata contract for ledger tooling."""
    normalized_details: dict[str, object] = {}
    if request.details:
        normalized_details.update(request.details)

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
    contract_ref = normalize_contract_ref(request.contract_ref)
    contract_version = normalize_contract_version(request.contract_version)
    _apply_optional_diagnostic_anchor(diagnostic, "pipeline", request.pipeline_name)
    _apply_optional_diagnostic_anchor(diagnostic, "provider", request.provider)
    _apply_optional_diagnostic_anchor(diagnostic, "entity", request.entity)
    _apply_optional_diagnostic_anchor(diagnostic, "run_type", request.run_type)
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
