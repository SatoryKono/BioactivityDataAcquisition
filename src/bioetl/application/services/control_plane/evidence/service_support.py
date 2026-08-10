"""Shared scope and payload helpers for control-plane evidence services."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.application.services.control_plane.evidence.models import (
    evidence_payload,
)
from bioetl.application.services.control_plane_evidence import EvidenceCheck
from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.ports import RunLedgerPort


@dataclass(frozen=True, slots=True)
class EvidenceScope:
    """Resolved selector context passed from the HTTP interface."""

    requested_pipeline: str
    selected_run_id: str | None
    selected_run_types: tuple[str, ...]
    resolved_via: str
    manifest: RunManifest | None


def service_payload(
    *,
    endpoint: str,
    scope: EvidenceScope,
    checks: tuple[EvidenceCheck, ...],
    additional_data: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the shared service payload from one resolved selector scope."""
    return evidence_payload(
        endpoint=endpoint,
        checks=checks,
        requested_pipeline=scope.requested_pipeline,
        selected_run_id=scope.selected_run_id,
        selected_run_types=scope.selected_run_types,
        resolved_via=scope.resolved_via,
        manifest=scope.manifest,
        additional_fields=additional_data,
    )


def source_error_payload(
    *,
    endpoint: str,
    scope: EvidenceScope,
    reason: str,
    check: str,
) -> dict[str, object]:
    """Return a stable source-read failure without raw exception text."""
    return service_payload(
        endpoint=endpoint,
        scope=scope,
        checks=(
            EvidenceCheck(
                check,
                "ERROR",
                reason,
                "Persisted control-plane evidence could not be read or parsed.",
            ),
        ),
    )


def ledger_entries(
    port: RunLedgerPort | None,
    manifest: RunManifest,
) -> tuple[RunLedgerEntry, ...]:
    """Load one manifest ledger as an immutable tuple."""
    if port is None:
        return ()
    return tuple(port.list_entries(manifest.manifest_id))


__all__ = [
    "EvidenceScope",
    "ledger_entries",
    "service_payload",
    "source_error_payload",
]
