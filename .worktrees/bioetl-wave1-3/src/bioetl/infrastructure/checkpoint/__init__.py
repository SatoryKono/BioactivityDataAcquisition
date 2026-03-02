"""Checkpoint storage implementations.

Provides:
- LocalCheckpoint: Local filesystem checkpoint storage
"""

from __future__ import annotations

from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint

__all__ = ["LocalCheckpoint"]
