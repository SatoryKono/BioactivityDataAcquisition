"""Locking implementations for local development.

Provides:
- MemoryLock: In-memory lock for single-process local development
"""

from bioetl.infrastructure.locking.memory_lock import MemoryLock

__all__ = ["MemoryLock"]
