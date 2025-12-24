"""Locking implementations for local development.

Provides:
- MemoryLock: In-memory lock for single-process local development
"""

from __future__ import annotations

from bioetl.infrastructure.locking.memory_lock import MemoryLock

__all__ = ["MemoryLock"]
