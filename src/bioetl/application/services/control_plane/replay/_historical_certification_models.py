"""Models and result assembly for historical replay certification workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from bioetl.application.services.control_plane.manifest.diagnostics import (
    build_diagnostics_summary as build_diagnostics_summary,
)
from bioetl.domain.control_plane import RunManifest
from bioetl.domain.ports import RunLedgerPort


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

    def build(
        self,
        *,
        manifest: RunManifest,
        certification_scope: str,
    ) -> HistoricalReplayCertificationResult:
        diagnostics = build_diagnostics_summary(
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


__all__ = [
    "HistoricalReplayCertificationProtocol",
    "HistoricalReplayCertificationResult",
    "HistoricalReplayCertificationResultAssembler",
    "_source_key",
]
