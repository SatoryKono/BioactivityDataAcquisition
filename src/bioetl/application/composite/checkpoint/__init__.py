"""Composite checkpoint facade.

Public API remains stable at:
- bioetl.application.composite.checkpoint.CompositeCheckpointState
- bioetl.application.composite.checkpoint.CompositeCheckpointService
- bioetl.application.composite.checkpoint.CompositeCheckpointManager
- bioetl.application.composite.checkpoint.ExpectedCheckpointContext
- bioetl.application.composite.checkpoint.create_expected_checkpoint_context
- bioetl.application.composite.checkpoint.merge_expected_anchors
- bioetl.application.composite.checkpoint.fresh_checkpoint_state
"""

from __future__ import annotations

from bioetl.application.composite.checkpoint._anchor_context import (
    ExpectedCheckpointContext,
    create_expected_checkpoint_context,
    fresh_checkpoint_state,
    merge_expected_anchors,
)
from bioetl.application.composite.checkpoint.service import (
    CompositeCheckpointManager,
    CompositeCheckpointService,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState

__all__ = [
    "CompositeCheckpointManager",
    "CompositeCheckpointService",
    "CompositeCheckpointState",
    "ExpectedCheckpointContext",
    "create_expected_checkpoint_context",
    "fresh_checkpoint_state",
    "merge_expected_anchors",
]
