"""Upstream lineage validation and certification result assembly."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from bioetl.domain.control_plane import RunLedgerEntry, RunManifest
from bioetl.domain.ports import RunLedgerPort, RunManifestPort

__all__ = [
    "DiagnosticsSummaryBuilder",
    "HistoricalReplayCertificationProtocol",
    "HistoricalReplayCertificationResult",
    "HistoricalReplayCertificationResultAssembler",
    "_source_key",
    "load_upstream_manifest",
    "validate_upstream_certification_state",
    "validate_upstream_presence",
    "validate_upstream_run_id_match",
]

DiagnosticsSummaryBuilder = Callable[
    [RunManifest, tuple[RunLedgerEntry, ...]],
    dict[str, object],
]


class HistoricalReplayCertificationProtocol(Protocol):
    @property
    def provider(self) -> str: ...

    @property
    def entity(self) -> str: ...

    @property
    def pipeline_name(self) -> str: ...

    @property
    def query(self) -> str | None: ...

    @property
    def upstream_run_id(self) -> str | None: ...

    @property
    def upstream_manifest_id(self) -> str | None: ...


@dataclass(frozen=True, slots=True)
class HistoricalReplayCertificationResult:
    manifest_id: str
    run_id: str
    certification_scope: str
    appended_snapshot_count: int
    replay_occurrence_kind: str
    broader_historical_exact_replay_state: str


@dataclass(frozen=True, slots=True)
class HistoricalReplayCertificationResultAssembler:
    ledger_port: RunLedgerPort
    summary_builder: DiagnosticsSummaryBuilder

    def build(
        self,
        *,
        manifest: RunManifest,
        certification_scope: str,
    ) -> HistoricalReplayCertificationResult:
        diagnostics = self.summary_builder(
            manifest,
            tuple(self.ledger_port.list_entries(manifest.manifest_id)),
        )
        input_snapshots = diagnostics.get("input_snapshots", [])
        appended_snapshot_count = (
            len(input_snapshots) if isinstance(input_snapshots, list) else 0
        )
        return HistoricalReplayCertificationResult(
            manifest_id=manifest.manifest_id,
            run_id=str(manifest.run_id),
            certification_scope=certification_scope,
            appended_snapshot_count=appended_snapshot_count,
            replay_occurrence_kind=str(
                diagnostics.get("replay_occurrence_kind") or "unknown"
            ),
            broader_historical_exact_replay_state=str(
                diagnostics.get("broader_historical_exact_replay_state") or "unknown"
            ),
        )


def _source_key(
    *,
    provider: str,
    entity: str,
    pipeline_name: str,
    query: str | None,
) -> tuple[str, str, str, str | None]:
    normalized_query = str(query).strip() or None if query is not None else None
    return (provider, entity, pipeline_name, normalized_query)


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
    summary_builder: DiagnosticsSummaryBuilder,
) -> None:
    diagnostics = summary_builder(
        upstream_manifest,
        tuple(ledger_port.list_entries(upstream_manifest.manifest_id)),
    )
    state = str(diagnostics.get("broader_historical_exact_replay_state") or "")
    if state != "historical_source_replay_certified":
        raise ValueError(
            "Composite certification requires upstream "
            "historical_source_replay_certified lineage"
        )
