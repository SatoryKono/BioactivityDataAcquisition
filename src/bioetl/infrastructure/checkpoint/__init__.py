"""Checkpoint storage implementations.

Provides:
- LocalCheckpointAdapter: Local filesystem checkpoint storage
"""

from __future__ import annotations

from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpointAdapter

__all__ = ["LocalCheckpointAdapter"]
