"""Shared identity models for historical replay inventory rows."""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Protocol

__all__ = [
    "HistoricalReplayRunIdentity",
    "HistoricalReplayRunIdentityRecord",
    "HistoricalReplayUniverseExternalRecord",
    "HistoricalReplayUniverseRecord",
    "build_historical_certified_identity_payload_from_record",
    "build_historical_identity_core_payload",
]


@dataclass(frozen=True, slots=True)
class HistoricalReplayRunIdentityRecord:
    """Core run identity anchors shared by historical replay inventory records."""

    manifest_id: str
    run_id: str
    pipeline_name: str
    provider: str
    entity: str
    execution_context: str


HistoricalReplayRunIdentity = HistoricalReplayRunIdentityRecord


class _HistoricalReplayCertifiedIdentity(Protocol):
    @property
    def manifest_id(self) -> str: ...

    @property
    def run_id(self) -> str: ...

    @property
    def pipeline_name(self) -> str: ...

    @property
    def provider(self) -> str: ...

    @property
    def entity(self) -> str: ...

    @property
    def execution_context(self) -> str: ...

    @property
    def certification_status(self) -> str: ...

    @property
    def replay_occurrence_kind(self) -> str: ...

    @property
    def blocking_reasons(self) -> tuple[str, ...]: ...


@dataclass(frozen=True, slots=True)
class HistoricalReplayUniverseExternalRecord(HistoricalReplayRunIdentity):
    """One authoritative non-local historical run record."""

    certification_status: str
    replay_occurrence_kind: str
    blocking_reasons: tuple[str, ...] = ()
    evidence_residency: str = "archived"
    durable_evidence_coverage: bool = False
    source_pack_ref: str | None = None

    def to_dict(self) -> dict[str, object]:
        return build_historical_certified_identity_payload_from_record(
            self,
            evidence_residency=self.evidence_residency,
            durable_evidence_coverage=self.durable_evidence_coverage,
            source_pack_ref=self.source_pack_ref,
        )


@dataclass(frozen=True, slots=True)
class HistoricalReplayUniverseRecord(HistoricalReplayRunIdentity):
    """One merged historical-run record in the full replay universe."""

    certification_status: str
    replay_occurrence_kind: str
    blocking_reasons: tuple[str, ...]
    universe_origin: str
    evidence_residency: str
    durable_evidence_coverage: bool
    source_pack_ref: str | None = None

    def to_dict(self) -> dict[str, object]:
        return build_historical_certified_identity_payload_from_record(
            self,
            universe_origin=self.universe_origin,
            evidence_residency=self.evidence_residency,
            durable_evidence_coverage=self.durable_evidence_coverage,
            source_pack_ref=self.source_pack_ref,
        )


def build_historical_certified_identity_payload_from_record(
    record: _HistoricalReplayCertifiedIdentity,
    **extra_fields: object,
) -> dict[str, object]:
    """Build one JSON-safe historical replay row from its identity record."""
    payload = build_historical_identity_core_payload(record)
    payload.update(
        {
            "certification_status": record.certification_status,
            "replay_occurrence_kind": record.replay_occurrence_kind,
            "blocking_reasons": list(record.blocking_reasons),
        }
    )
    conflicting_fields = set(extra_fields).intersection(payload)
    if conflicting_fields:
        raise ValueError(
            "Extra fields cannot override certified identity fields: "
            f"{sorted(conflicting_fields)}"
        )
    payload.update(extra_fields)
    return payload


def build_historical_identity_core_payload(
    identity: HistoricalReplayRunIdentity | _HistoricalReplayCertifiedIdentity,
) -> dict[str, object]:
    """Return the shared core payload for one historical replay identity row."""
    return {
        field.name: getattr(identity, field.name)
        for field in fields(HistoricalReplayRunIdentityRecord)
    }
