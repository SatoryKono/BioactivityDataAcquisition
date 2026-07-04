"""Public atomic-write facade for infrastructure storage utilities."""

from __future__ import annotations

from bioetl.infrastructure.storage.support.atomic_ops import (
    AtomicWriteError,
    atomic_write,
    atomic_write_bytes,
    atomic_write_text,
)

__all__ = [
    "AtomicWriteError",
    "atomic_write",
    "atomic_write_bytes",
    "atomic_write_text",
]
