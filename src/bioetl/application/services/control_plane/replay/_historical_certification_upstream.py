"""Upstream lineage validation helpers for historical replay certification."""

from __future__ import annotations

from bioetl.application.services.control_plane.replay._historical_certification_models import (
    HistoricalReplayCertificationProtocol,
    build_diagnostics_summary,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.ports import RunLedgerPort, RunManifestPort

__all__ = [
    "load_upstream_manifest",
    "validate_upstream_certification_state",
    "validate_upstream_presence",
    "validate_upstream_run_id_match",
]


def validate_upstream_presence(
    certification: HistoricalReplayCertificationProtocol,
) -> None:
    upstream_manifest_id = str(certification.upstream_manifest_id or "").strip()
    upstream_run_id = str(certification.upstream_run_id or "").strip()
    if not upstream_manifest_id or not upstream_run_id:
        raise ValueError(
            "Composite certification requires upstream_run_id and upstream_manifest_id"
        )


def load_upstream_manifest(
    *,
    manifest_port: RunManifestPort,
    certification: HistoricalReplayCertificationProtocol,
) -> RunManifest:
    upstream_manifest_id = str(certification.upstream_manifest_id or "").strip()
    upstream_manifest = manifest_port.get(upstream_manifest_id)
    if upstream_manifest is None:
        raise ValueError(f"Upstream manifest {upstream_manifest_id!r} was not found")
    return upstream_manifest


def validate_upstream_run_id_match(
    *,
    certification: HistoricalReplayCertificationProtocol,
    upstream_manifest: RunManifest,
) -> None:
    upstream_run_id = str(certification.upstream_run_id or "").strip()
    if upstream_run_id != str(upstream_manifest.run_id):
        raise ValueError(
            "Composite certification upstream_run_id does not match the persisted "
            "upstream manifest"
        )


def validate_upstream_certification_state(
    *,
    ledger_port: RunLedgerPort,
    upstream_manifest: RunManifest,
) -> None:
    diagnostics = build_diagnostics_summary(
        upstream_manifest,
        tuple(ledger_port.list_entries(upstream_manifest.manifest_id)),
    )
    state = str(diagnostics.get("broader_historical_exact_replay_state") or "")
    if state != "historical_source_replay_certified":
        raise ValueError(
            "Composite certification requires upstream "
            "historical_source_replay_certified lineage"
        )
