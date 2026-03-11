"""Compatibility shim for checkpoint manager imports.

Keeps the historical ``bioetl.application.core.checkpoint_manager`` import path
stable while the implementation lives under ``application.core.lifecycle``.
"""

from __future__ import annotations

from bioetl.application.core.lifecycle.checkpoint_manager import (
    CheckpointManager,
    CheckpointManagerService,
)

__all__ = ["CheckpointManager", "CheckpointManagerService"]
