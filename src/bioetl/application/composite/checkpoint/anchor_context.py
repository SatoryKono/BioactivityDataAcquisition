"""Legacy import shim for composite checkpoint anchor-context imports.

New first-party governance consumers must import these helpers from the package
root facade ``bioetl.application.composite.checkpoint``. This module remains
only as a compatibility-only shim for older imports.
"""

from __future__ import annotations

from bioetl.application.composite.checkpoint._anchor_context import (
    ExpectedCheckpointContext,
    create_expected_checkpoint_context,
    fresh_checkpoint_state,
    merge_expected_anchors,
)

__all__ = [
    "ExpectedCheckpointContext",
    "create_expected_checkpoint_context",
    "fresh_checkpoint_state",
    "merge_expected_anchors",
]
