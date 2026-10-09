"""Shared identity models for historical replay inventory rows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from bioetl.domain.control_plane.historical_replay_identity import (
    HistoricalReplayRunIdentityRecord,
)
from bioetl.domain.control_plane.historical_replay_identity import (
    build_historical_certification_payload as _build_historical_certification_payload,
)
from bioetl.domain.control_plane.historical_replay_identity import (
    build_historical_certified_identity_payload as _build_historical_certified_identity_payload,
)
from bioetl.domain.control_plane.historical_replay_identity import (
    build_historical_certified_identity_payload_from_record as _build_historical_certified_identity_payload_from_record,
)
from bioetl.domain.control_plane.historical_replay_identity import (
    build_historical_identity_core_payload as _build_historical_identity_core_payload,
)
from bioetl.domain.control_plane.historical_replay_identity import (
    build_historical_run_identity_payload as _build_historical_run_identity_payload,
)

__all__ = [
    "HistoricalReplayRunIdentity",
    "HistoricalReplayRunIdentityRecord",
    "HistoricalReplayUniverseExternalRecord",
    "HistoricalReplayUniverseRecord",
    "build_historical_certification_payload",
    "build_historical_certified_identity_payload",
    "build_historical_certified_identity_payload_from_record",
    "build_historical_identity_core_payload",
    "build_historical_run_identity_payload",
]


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
    return _build_historical_certified_identity_payload_from_record(
        record,
        **extra_fields,
    )


def build_historical_identity_core_payload(
    identity: HistoricalReplayRunIdentity | _HistoricalReplayCertifiedIdentity,
) -> dict[str, object]:
    """Return the shared core payload for one historical replay identity row."""
    return _build_historical_identity_core_payload(identity)


def build_historical_run_identity_payload(
    *,
    manifest_id: str,
    run_id: str,
    pipeline_name: str,
    provider: str,
    entity: str,
    execution_context: str,
    certification_status: str,
    replay_occurrence_kind: str,
    blocking_reasons: tuple[str, ...] = (),
    **extra_fields: object,
) -> dict[str, object]:
    """Return one JSON-safe historical run identity payload."""
    return _build_historical_run_identity_payload(
        manifest_id=manifest_id,
        run_id=run_id,
        pipeline_name=pipeline_name,
        provider=provider,
        entity=entity,
        execution_context=execution_context,
        certification_status=certification_status,
        replay_occurrence_kind=replay_occurrence_kind,
        blocking_reasons=blocking_reasons,
        **extra_fields,
    )


def build_historical_certification_payload(
    *,
    certification_status: str,
    replay_occurrence_kind: str,
    blocking_reasons: tuple[str, ...] = (),
) -> dict[str, object]:
    """Return common certification fields shared by historical replay rows."""
    return _build_historical_certification_payload(
        certification_status=certification_status,
        replay_occurrence_kind=replay_occurrence_kind,
        blocking_reasons=blocking_reasons,
    )


def build_historical_certified_identity_payload(
    identity: HistoricalReplayRunIdentity,
    *,
    certification_status: str,
    replay_occurrence_kind: str,
    blocking_reasons: tuple[str, ...] = (),
    **extra_fields: object,
) -> dict[str, object]:
    """Return one JSON-safe historical replay row with shared identity anchors."""
    return _build_historical_certified_identity_payload(
        identity,
        certification_status=certification_status,
        replay_occurrence_kind=replay_occurrence_kind,
        blocking_reasons=blocking_reasons,
        **extra_fields,
    )
