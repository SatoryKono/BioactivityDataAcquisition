"""Checkpoint contracts shared by the composite runner's merge modules."""

from __future__ import annotations

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointService,
    CompositeCheckpointState,
)

__all__ = ["CompositeCheckpointService", "CompositeCheckpointState"]
