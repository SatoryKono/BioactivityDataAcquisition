"""Entry-construction helpers for append-only run-ledger events."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Protocol, cast

from bioetl.application.services.control_plane.ledger.diagnostic_support import (
    _RunLedgerCorrelationFieldsProtocol,
    build_run_ledger_diagnostic_details,
    build_run_ledger_diagnostic_request,
)
from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane.run_ledger import infer_ledger_event_family
from bioetl.domain.normalization import normalize_run_ledger_payload
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


class _RunLedgerServiceEntryProtocol(_RunLedgerCorrelationFieldsProtocol, Protocol):
    ledger_port: _RunLedgerPortProtocol
    manifest_id: str
    run_id: object
    composite_run_id: str | None
    _entry_id_factory: Callable[[], str]
    _occurred_at_factory: Callable[[], datetime]


def build_run_ledger_idempotency_key(payload: Mapping[str, object]) -> str:
    """Build a stable key for one logical lifecycle event."""
    semantic_payload = {
        field_name: payload.get(field_name) for field_name in _IDEMPOTENCY_KEY_FIELDS
    }
    serialized = json.dumps(
        semantic_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return f"sha256:{sha256(serialized.encode('utf-8')).hexdigest()}"


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
                    run_id=cast(RunID, service.run_id),
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
