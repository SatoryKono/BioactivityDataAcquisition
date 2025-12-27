"""Audit infrastructure - file-based audit logging.

Provides implementation of AuditPort for write operation traceability.
"""

from __future__ import annotations

from bioetl.infrastructure.audit.file_audit import FileAuditAdapter

__all__ = [
    "FileAuditAdapter",
]
