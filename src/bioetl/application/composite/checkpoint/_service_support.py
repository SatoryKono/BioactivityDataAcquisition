"""Compatibility facade for composite checkpoint support helpers."""

from __future__ import annotations

from bioetl.application.composite.checkpoint._anchor_context import (
    ExpectedCheckpointContext,
    create_expected_checkpoint_context,
    fresh_checkpoint_state,
    merge_expected_anchors,
)
from bioetl.application.composite.checkpoint._checkpoint_runtime import (
    CHECKPOINT_READ_ERRORS,
    CHECKPOINT_WRITE_ERRORS,
    latest_checkpoint_filename,
    load_checkpoint_state,
    resolve_resume_checkpoint_filename,
    warn_if_checkpoint_exists_with_progress,
    warn_if_checkpoint_stale,
)
from bioetl.application.composite.checkpoint._resume_compatibility import (
    validate_resume_compatibility,
)

__all__ = [
    "CHECKPOINT_READ_ERRORS",
    "CHECKPOINT_WRITE_ERRORS",
    "ExpectedCheckpointContext",
    "create_expected_checkpoint_context",
    "fresh_checkpoint_state",
    "latest_checkpoint_filename",
    "load_checkpoint_state",
    "merge_expected_anchors",
    "resolve_resume_checkpoint_filename",
    "validate_resume_compatibility",
    "warn_if_checkpoint_exists_with_progress",
    "warn_if_checkpoint_stale",
]
