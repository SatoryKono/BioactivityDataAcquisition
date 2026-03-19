"""Path and timing helpers for Bronze metadata side effects."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

__all__ = [
    "calculate_bronze_completed_at",
    "resolve_bronze_metadata_base_path",
]


def calculate_bronze_completed_at(
    ingestion_ts: datetime,
    duration: float,
) -> datetime:
    """Calculate deterministic Bronze completion time from start + duration."""
    return ingestion_ts + timedelta(seconds=duration)


def resolve_bronze_metadata_base_path(
    *,
    base_path: Path,
    provider: str,
    entity: str,
    flat_structure: bool,
) -> Path:
    """Resolve base path for Bronze metadata sidecar output."""
    if flat_structure:
        return base_path
    return base_path / provider / entity
