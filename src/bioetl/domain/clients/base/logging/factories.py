"""Stub factories for logging-related client adapters."""

from bioetl.domain.clients.base.logging.contracts import TracerABC


def default_tracer() -> TracerABC:
    """Placeholder tracer factory until concrete tracer is provided."""

    raise NotImplementedError("TracerABC default factory is not configured")


__all__ = ["default_tracer"]

