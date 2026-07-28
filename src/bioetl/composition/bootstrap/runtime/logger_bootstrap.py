"""Logger bootstrap helpers for runtime observability wiring."""

from __future__ import annotations

from collections.abc import Callable
from itertools import count
from os import getpid
from typing import TYPE_CHECKING
from uuid import NAMESPACE_OID, UUID, uuid5

from bioetl.domain.ports import LoggerPort

if TYPE_CHECKING:
    LoggerFactory = Callable[[str, UUID, str], LoggerPort]

__all__ = [
    "bootstrap_logger",
]

_FALLBACK_LOG_RUN_ID_COUNTER = count()

def _fallback_log_correlation_run_id() -> UUID:
    """Return a deterministic process-local fallback log correlation ID."""
    occurrence = next(_FALLBACK_LOG_RUN_ID_COUNTER)
    return uuid5(NAMESPACE_OID, f"bioetl.logger_bootstrap:{getpid()}:{occurrence}")

def _default_logger_factory(pipeline: str, run_id: UUID, log_level: str) -> LoggerPort:
    """Create a UnifiedLogger with standard runtime settings."""
    from bioetl.infrastructure.observability.unified_logger import UnifiedLogger

    return UnifiedLogger(
        pipeline=pipeline,
        run_id=run_id,
        log_level=log_level,
        json_format=True,
    )

def bootstrap_logger(
    pipeline: str,
    run_id: UUID | None = None,
    log_level: str = "INFO",
    logger_factory: LoggerFactory | None = None,
) -> LoggerPort:
    """Create a logger port implementation for pipeline execution.

    Args:
        pipeline: Pipeline name used as a structured log field (e.g., 'chembl_activity').
        run_id: Run UUID for log correlation; a deterministic process-local
            occurrence ID is generated if None.
        log_level: Minimum log level string (e.g., 'INFO', 'DEBUG').
        logger_factory: Optional factory callable for DI/testing; uses UnifiedLogger
            with JSON format when None.

    Returns:
        Configured LoggerPort for structured pipeline logging.
    """
    effective_run_id = (
        run_id if run_id is not None else _fallback_log_correlation_run_id()
    )
    factory = logger_factory or _default_logger_factory
    return factory(pipeline, effective_run_id, log_level)
