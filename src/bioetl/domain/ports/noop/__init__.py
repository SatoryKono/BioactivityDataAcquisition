"""No-op implementations facade for observability and utility ports."""

from bioetl.domain.ports.noop._audit_pii import NoOpAudit, NoOpPiiHasher
from bioetl.domain.ports.noop._memory_metadata import (
    NoOpMemoryMonitor,
    NoOpMetadataWriter,
)
from bioetl.domain.ports.noop._metrics import NoOpMetrics
from bioetl.domain.ports.noop._tracing import NoOpTracing, _NoOpOtelTracer, _NoOpSpan

__all__ = [
    "NoOpAudit",
    "NoOpMemoryMonitor",
    "NoOpMetadataWriter",
    "NoOpMetrics",
    "NoOpPiiHasher",
    "NoOpTracing",
    "_NoOpOtelTracer",
    "_NoOpSpan",
]
