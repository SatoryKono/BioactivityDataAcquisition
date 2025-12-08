"""Stub factories for logging-related client adapters."""

from bioetl.interfaces.observability import TracingPortABC


def default_tracer() -> TracingPortABC:
    """Placeholder tracer factory until concrete tracer is provided."""

    raise NotImplementedError("TracingPortABC default factory is not configured")


__all__ = ["default_tracer"]
