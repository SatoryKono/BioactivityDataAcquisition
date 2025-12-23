"""Checkpoint storage implementations.

Provides:
- LocalCheckpoint: Local filesystem checkpoint storage
"""

from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint

__all__ = ["LocalCheckpoint"]
