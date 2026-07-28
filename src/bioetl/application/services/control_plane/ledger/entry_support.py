"""Entry-construction helpers for append-only run-ledger events."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from bioetl.application.services.control_plane.ledger.diagnostic_support import (
    LEDGER_DIAGNOSTIC_CONTRACT_VERSION,
    RunLedgerCorrelationFieldsProtocol,
    _RunLedgerDiagnosticRequest,
    build_run_ledger_diagnostic_request,
)
from bioetl.application.services.control_plane.ledger.idempotency import (
    build_control_plane_idempotency_key,
)
from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane.run_ledger import infer_ledger_event_family
from bioetl.domain.normalization import (
    normalize_contract_ref,
    normalize_contract_version,
    normalize_control_plane_opaque_hash_ref,
    normalize_run_ledger_payload,
)
from bioetl.domain.ports import RunLedgerPort
from bioetl.domain.types import RunID

_IDEMPOTENCY_KEY_FIELDS = (
    "manifest_id",
    "run_id",
    "event_type",
    "event_family",
    "status",
    "stage",
    "message",
    "error_type",
    "dataset_ref",
    "lineage_fragment_id",
    "metrics_snapshot",
    "details",
)


@dataclass(slots=True)
class RunLedgerEntryRequest:
    event_type: str
    status: str | None
    stage: str | None = None
    message: str | None = None
    error_type: str | None = None
    dataset_ref: str | None = None
    lineage_fragment_id: str | None = None
    metrics_snapshot: dict[str, int] | None = None
    details: dict[str, object] | None = None


class _RunLedgerServiceEntryProtocol(RunLedgerCorrelationFieldsProtocol, Protocol):
    @property
    def ledger_port(self) -> RunLedgerPort: ...

    @property
    def manifest_id(self) -> str: ...

    @property
    def run_id(self) -> RunID: ...

    @property
    def composite_run_id(self) -> str | None: ...

    @property
    def _entry_id_factory(self) -> Callable[[], str]: ...

    @property
    def _occurred_at_factory(self) -> Callable[[], datetime]: ...


def build_run_ledger_idempotency_key(payload: Mapping[str, object]) -> str:
    """Build a stable key for one logical lifecycle event."""
    return build_control_plane_idempotency_key(
        payload,
        fields=_IDEMPOTENCY_KEY_FIELDS,
    )


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


def validate_manifest_linkage(service: _RunLedgerServiceEntryProtocol) -> None:
    """Reject lifecycle events that are not tied to a persisted manifest."""
    manifest_id = service.manifest_id.strip()
    if not manifest_id or manifest_id == "pending":
        raise RuntimeError(
            "Run ledger events require a persisted manifest_id before append"
        )


def append_run_ledger_entry(
    service: _RunLedgerServiceEntryProtocol,
    request: RunLedgerEntryRequest,
) -> RunLedgerEntry:
    """Create and append one ledger entry."""
    validate_manifest_linkage(service)
    event_family = infer_ledger_event_family(request.event_type)
    payload = normalize_run_ledger_payload(
        {
            "entry_id": service._entry_id_factory(),
            "manifest_id": service.manifest_id,
            "run_id": service.run_id,
            "event_type": request.event_type,
            "event_family": event_family,
            "occurred_at": service._occurred_at_factory(),
            "status": request.status,
            "stage": request.stage,
            "message": request.message,
            "error_type": request.error_type,
            "dataset_ref": request.dataset_ref,
            "lineage_fragment_id": request.lineage_fragment_id,
            "metrics_snapshot": request.metrics_snapshot,
            "details": build_run_ledger_diagnostic_details(
                build_run_ledger_diagnostic_request(
                    service,
                    event_type=request.event_type,
                    event_family=event_family,
                    manifest_id=service.manifest_id,
                    run_id=service.run_id,
                    composite_run_id=service.composite_run_id,
                    status=request.status,
                    stage=request.stage,
                    error_type=request.error_type,
                    dataset_ref=request.dataset_ref,
                    lineage_fragment_id=request.lineage_fragment_id,
                    details=request.details,
                )
            ),
        }
    )
    payload["idempotency_key"] = build_run_ledger_idempotency_key(payload)
    entry = RunLedgerEntry.from_dict(payload)
    service.ledger_port.append(entry)
    return entry


def append_run_outcome(
    service: _RunLedgerServiceEntryProtocol,
    *,
    event_type: str,
    status: str,
    metrics_snapshot: dict[str, int],
    message: str | None = None,
    error_type: str | None = None,
    details: dict[str, object] | None = None,
) -> RunLedgerEntry:
    """Append one terminal run outcome with the canonical payload shape."""
    return append_run_ledger_entry(
        service,
        RunLedgerEntryRequest(
            event_type=event_type,
            status=status,
            message=message,
            error_type=error_type,
            metrics_snapshot=metrics_snapshot,
            details=details,
        ),
    )


__all__ = [
    "RunLedgerEntryRequest",
    "append_run_ledger_entry",
    "append_run_outcome",
    "build_run_ledger_idempotency_key",
    "validate_manifest_linkage",
]
