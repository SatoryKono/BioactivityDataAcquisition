"""Logging utilities for adapters.

Provides standardized error logging format across all data source adapters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import structlog


def log_adapter_error(
    logger: structlog.BoundLogger,
    provider: str,
    operation: str,
    *,
    exc_info: bool = True,
    **context: Any,
) -> None:
    """Log adapter error in standardized format.

    Формат сообщения: "{provider} {operation} failed"

    Args:
        logger: Structlog logger instance
        provider: Provider name (e.g., "chembl", "pubchem", "uniprot")
        operation: Operation that failed (e.g., "fetch", "batch fetch", "health check")
        exc_info: Include exception traceback (default: True)
        **context: Additional context fields to include in log

    Example:
        >>> log_adapter_error(
        ...     logger,
        ...     provider="pubchem",
        ...     operation="compound batch fetch",
        ...     batch_start=100,
        ...     batch_end=199,
        ... )
        # Logs: "pubchem compound batch fetch failed" with context fields
    """
    message = f"{provider} {operation} failed"
    logger.error(message, exc_info=exc_info, **context)
