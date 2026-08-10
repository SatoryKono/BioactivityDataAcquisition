"""Bounded manifest-to-ledger referential-integrity observability."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane.run_ledger import MANIFEST_CREATED_EVENT
from bioetl.domain.exceptions import BioETLError

if TYPE_CHECKING:
    from bioetl.domain.control_plane import RunManifest
    from bioetl.domain.ports import MetricsPort, RunLedgerPort, RunManifestPort

MANIFEST_LEDGER_INTEGRITY_METRIC = "bioetl_manifest_ledger_integrity_ratio"

_CONSISTENT = "consistent"
_INCONSISTENT = "inconsistent"
_INTEGRITY_TYPES = (_CONSISTENT, _INCONSISTENT)
_LEDGER_FLAG_KEYS = ("run_ledger_enabled", "ledger_enabled")
_NESTED_CONFIG_KEYS = ("pipeline", "control_plane", "settings")
_READ_FAILURES = (BioETLError, OSError, RuntimeError, TypeError, ValueError)


@dataclass(frozen=True, slots=True)
class ManifestLedgerIntegritySummary:
    """Aggregate referential-integrity result for one bounded run scope."""

    pipeline: str
    run_type: str
    consistent: int
    inconsistent: int

    @property
    def denominator(self) -> int:
        """Return the number of ledger-expected manifests in this scope."""
        return self.consistent + self.inconsistent

    @property
    def consistent_ratio(self) -> float:
        """Return the consistent share; zero when there is no denominator."""
        return self.consistent / self.denominator if self.denominator else 0.0

    @property
    def inconsistent_ratio(self) -> float:
        """Return the inconsistent share; zero when there is no denominator."""
        return self.inconsistent / self.denominator if self.denominator else 0.0


def _as_mapping(value: object) -> Mapping[str, object] | None:
    return value if isinstance(value, Mapping) else None


def _parse_explicit_bool(value: object) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"false", "0", "no", "off"}:
            return False
        if normalized in {"true", "1", "yes", "on"}:
            return True
    return None


def _iter_candidate_configs(manifest: RunManifest) -> tuple[Mapping[str, object], ...]:
    candidates: list[Mapping[str, object]] = []
    pending: list[Mapping[str, object]] = []
    for raw in (
        manifest.launch_context,
        manifest.runtime_config,
        manifest.resolved_config,
    ):
        mapping = _as_mapping(raw)
        if mapping is not None:
            pending.append(mapping)
    while pending:
        current = pending.pop(0)
        candidates.append(current)
        for key in _NESTED_CONFIG_KEYS:
            nested = _as_mapping(current.get(key))
            if (
                nested is not None
                and nested not in candidates
                and nested not in pending
            ):
                pending.append(nested)
    return tuple(candidates)


def manifest_expects_ledger(manifest: RunManifest) -> bool:
    """Return the explicit ledger flag, defaulting legacy manifests to enabled."""
    for config in _iter_candidate_configs(manifest):
        for key in _LEDGER_FLAG_KEYS:
            explicit = _parse_explicit_bool(config.get(key))
            if explicit is not None:
                return explicit
    return True


def _entry_identity(entry: RunLedgerEntry) -> tuple[object, ...]:
    return (
        entry.entry_id,
        entry.manifest_id,
        entry.run_id,
        entry.event_type,
        entry.occurred_at,
    )


def _ledger_matches_manifest(
    manifest: RunManifest,
    ledger_port: RunLedgerPort,
) -> bool:
    try:
        entries = tuple(ledger_port.list_entries(manifest.manifest_id))
        entries_by_run = tuple(ledger_port.list_entries_by_run_id(manifest.run_id))
    except _READ_FAILURES:
        return False
    if not entries or entries[0].event_type != MANIFEST_CREATED_EVENT:
        return False
    if sum(entry.event_type == MANIFEST_CREATED_EVENT for entry in entries) != 1:
        return False
    if any(
        entry.manifest_id != manifest.manifest_id or entry.run_id != manifest.run_id
        for entry in entries
    ):
        return False
    return tuple(map(_entry_identity, entries_by_run)) == tuple(
        map(_entry_identity, entries)
    )


@dataclass(slots=True, kw_only=True)
class ControlPlaneIntegrityMetricsService:
    """Refresh bounded integrity gauges from a full control-plane catalog scan."""

    manifest_port: RunManifestPort
    ledger_port: RunLedgerPort
    metrics: MetricsPort
    _emitted_scopes: set[tuple[str, str]] = field(
        default_factory=set,
        init=False,
        repr=False,
    )

    def refresh(self) -> tuple[ManifestLedgerIntegritySummary, ...]:
        """Reconcile all persisted manifests and atomically refresh scope ratios."""
        counts: dict[tuple[str, str], list[int]] = {}
        for manifest in self.manifest_port.list_all():
            if not manifest_expects_ledger(manifest):
                continue
            scope = (manifest.pipeline_name, manifest.run_type.value)
            scope_counts = counts.setdefault(scope, [0, 0])
            scope_counts[
                0 if _ledger_matches_manifest(manifest, self.ledger_port) else 1
            ] += 1

        results = tuple(
            ManifestLedgerIntegritySummary(
                pipeline=pipeline,
                run_type=run_type,
                consistent=scope_counts[0],
                inconsistent=scope_counts[1],
            )
            for (pipeline, run_type), scope_counts in sorted(counts.items())
        )
        active_scopes = set(counts)
        for stale_scope in sorted(self._emitted_scopes - active_scopes):
            self._set_scope_ratios(stale_scope, consistent=0.0, inconsistent=0.0)
        for result in results:
            self._set_scope_ratios(
                (result.pipeline, result.run_type),
                consistent=result.consistent_ratio,
                inconsistent=result.inconsistent_ratio,
            )
        self._emitted_scopes = active_scopes
        return results

    def _set_scope_ratios(
        self,
        scope: tuple[str, str],
        *,
        consistent: float,
        inconsistent: float,
    ) -> None:
        pipeline, run_type = scope
        values = {_CONSISTENT: consistent, _INCONSISTENT: inconsistent}
        for integrity_type in _INTEGRITY_TYPES:
            self.metrics.set_gauge(
                MANIFEST_LEDGER_INTEGRITY_METRIC,
                values[integrity_type],
                {
                    "pipeline": pipeline,
                    "run_type": run_type,
                    "integrity_type": integrity_type,
                },
            )


__all__ = [
    "MANIFEST_LEDGER_INTEGRITY_METRIC",
    "ControlPlaneIntegrityMetricsService",
    "ManifestLedgerIntegritySummary",
    "manifest_expects_ledger",
]
