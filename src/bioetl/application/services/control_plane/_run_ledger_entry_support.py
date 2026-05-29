"""Entry-construction helpers for append-only run-ledger events."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from bioetl.application.services.control_plane._run_ledger_diagnostic_support import (
    _RunLedgerDiagnosticRequest,
    build_run_ledger_diagnostic_details,
)
from bioetl.application.services.control_plane.ledger_identity_support import (
    build_ledger_idempotency_key,
)
from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane.run_ledger import infer_ledger_event_family
from bioetl.domain.normalization import normalize_run_ledger_payload

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


class _RunLedgerPortProtocol(Protocol):
    def append(self, entry: RunLedgerEntry) -> None: ...


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


class _RunLedgerServiceEntryProtocol(Protocol):
    ledger_port: _RunLedgerPortProtocol
    manifest_id: str
    run_id: object
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
    _entry_id_factory: Callable[[], str]
    _occurred_at_factory: Callable[[], datetime]


def build_run_ledger_idempotency_key(payload: Mapping[str, object]) -> str:
    """Build a stable key for one logical lifecycle event."""
    return build_ledger_idempotency_key(payload, fields=_IDEMPOTENCY_KEY_FIELDS)


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
                _RunLedgerDiagnosticRequest(
                    event_type=request.event_type,
                    event_family=event_family,
                    manifest_id=service.manifest_id,
                    run_id=service.run_id,
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
                    dq_contract_compatibility_hash=(
                        service.dq_contract_compatibility_hash
                    ),
                    effective_config_artifact_id=service.effective_config_artifact_id,
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
