"""Shared identity models for historical replay inventory rows."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["HistoricalReplayRunIdentity"]


@dataclass(frozen=True, slots=True)
class HistoricalReplayRunIdentity:
    """Core run identity anchors shared by historical replay inventory records."""

    manifest_id: str
    run_id: str
    pipeline_name: str
    provider: str
    entity: str
    execution_context: str
