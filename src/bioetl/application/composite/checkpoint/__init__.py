"""Composite checkpoint facade.

This package root is the sanctioned public import surface for checkpoint
governance consumers. New first-party imports should target
``bioetl.application.composite.checkpoint`` rather than helper submodules.

Public API remains stable at:
- bioetl.application.composite.checkpoint.CompositeCheckpointState
- bioetl.application.composite.checkpoint.CompositeCheckpointService
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
    CompositeCheckpointService,
    CompositeCheckpointServiceContext,
)
from bioetl.application.composite.checkpoint.state import CompositeCheckpointState

__all__ = [
    "CompositeCheckpointService",
    "CompositeCheckpointServiceContext",
    "CompositeCheckpointState",
    "ExpectedCheckpointContext",
    "create_expected_checkpoint_context",
    "fresh_checkpoint_state",
    "merge_expected_anchors",
]
