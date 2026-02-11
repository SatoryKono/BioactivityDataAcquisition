"""No-op implementation of TracingPort.

Re-exports NoOpTracing from domain.ports.noop (single source of truth).
Infrastructure module kept for backward compatibility of import paths.

See also: bioetl.domain.ports.noop.NoOpTracing
"""

from __future__ import annotations

from bioetl.domain.ports.noop import NoOpTracing

__all__ = ["NoOpTracing"]
