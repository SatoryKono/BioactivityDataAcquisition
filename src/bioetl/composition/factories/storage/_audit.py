"""Audit wiring helpers for canonical storage factory assembly."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports import AuditPort
from bioetl.domain.ports.noop import NoOpAudit
from bioetl.infrastructure.audit.file_audit import FileAuditAdapter

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.infrastructure.config import Settings

__all__ = ["create_audit_port"]


def create_audit_port(
    *,
    settings: Settings,
    logger: LoggerPort,
    metrics: MetricsPort | None = None,
    tracing: TracingPort | None = None,
) -> AuditPort:
    """Create the canonical audit port for storage runtime wiring.

    Returns a concrete file-backed audit adapter when audit logging is enabled,
    otherwise returns an explicit ``NoOpAudit``.
    """
    observability = settings.observability
    if not observability.audit_enabled:
        return NoOpAudit()

    base_path = observability.audit_base_path
    resolved_path = (
        Path(base_path)
        if base_path is not None
        else _default_audit_path(settings=settings)
    )
    return FileAuditAdapter(
        base_path=resolved_path,
        logger=logger,
        metrics=metrics,
        tracing=tracing,
    )


def _default_audit_path(*, settings: Settings) -> Path:
    """Return the default audit directory under the managed output root."""
    return settings.data_dir / "output" / "audit"
