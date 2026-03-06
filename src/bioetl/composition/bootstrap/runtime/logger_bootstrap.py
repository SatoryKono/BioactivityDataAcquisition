"""Logger bootstrap helpers for runtime observability wiring."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from bioetl.domain.ports import LoggerPort
from bioetl.infrastructure.observability import UnifiedLogger

if TYPE_CHECKING:
    LoggerFactory = Callable[[str, UUID, str], LoggerPort]


__all__ = [
    "bootstrap_logger",
    "bootstrap_logger_port",
]


def _default_logger_factory(pipeline: str, run_id: UUID, log_level: str) -> LoggerPort:
    """Create a UnifiedLogger with standard runtime settings."""
    return UnifiedLogger(
        pipeline=pipeline,
        run_id=run_id,
        log_level=log_level,
        json_format=True,
    )


def bootstrap_logger_port(
    pipeline: str,
    run_id: UUID | None = None,
    log_level: str = "INFO",
    logger_factory: LoggerFactory | None = None,
) -> LoggerPort:
    """Create a logger port implementation for pipeline execution."""
    effective_run_id = run_id if run_id is not None else uuid4()
    factory = logger_factory or _default_logger_factory
    return factory(pipeline, effective_run_id, log_level)


def bootstrap_logger(
    pipeline: str,
    run_id: UUID | None = None,
    log_level: str = "INFO",
    logger_factory: LoggerFactory | None = None,
) -> LoggerPort:
    """Deprecated alias for :func:`bootstrap_logger_port`."""
    return bootstrap_logger_port(
        pipeline=pipeline,
        run_id=run_id,
        log_level=log_level,
        logger_factory=logger_factory,
    )
