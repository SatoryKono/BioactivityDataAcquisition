"""Shared identity models for historical replay inventory rows."""

from __future__ import annotations

from dataclasses import dataclass, fields

__all__ = [
    "build_historical_identity_core_payload",
    "HistoricalReplayRunIdentity",
    "HistoricalReplayRunIdentityRecord",
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


def build_historical_identity_core_payload(
    identity: HistoricalReplayRunIdentity,
) -> dict[str, object]:
    """Return the shared core payload for one historical replay identity row."""
    return {
        field.name: getattr(identity, field.name)
        for field in fields(HistoricalReplayRunIdentityRecord)
    }
