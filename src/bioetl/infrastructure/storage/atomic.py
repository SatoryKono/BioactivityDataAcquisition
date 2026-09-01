"""Public atomic-write facade for infrastructure storage utilities.

Re-exports the stable atomic I/O surface from
``bioetl.infrastructure.storage.support.atomic_ops``.

Release / migration notes
-------------------------
- **Normative contract:** docs/00-project/RULES.md section 4.3 requires
  same-filesystem temporary files followed by atomic publication.
- **Public symbols:** ``AtomicWriteError``, ``atomic_write``, ``atomic_write_bytes``,
  ``atomic_write_text`` — re-exports only; implementation lives under ``support/``.
- **Migration:** Prefer importing from this facade; direct imports from
  ``support.atomic_ops`` remain supported for reverse compatibility.
- **Rollback:** Removing a re-export would be a breaking change; restore the
  symbol in ``__all__`` and re-export from ``support.atomic_ops``. No schema or
  on-disk format change is associated with this facade module itself.
"""

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
