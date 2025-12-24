"""Logging utilities for adapters.

Provides standardized error logging format across all data source adapters.
"""

from __future__ import annotations

import logging
from typing import Any


def log_adapter_error(
    logger: Any,
    provider: str,
    operation: str,
    *,
    exc_info: bool = True,
    **context: Any,
) -> None:
    """Log adapter error in standardized format.

    Формат сообщения: "{provider} {operation} failed"

    Args:
        logger: Structlog logger or standard logging.Logger instance
        provider: Provider name (e.g., "chembl", "pubchem", "uniprot")
        operation: Operation that failed (e.g., "fetch", "batch fetch", "health check")
        exc_info: Include exception traceback (default: True)
        **context: Additional context fields to include in log

    """
    message = f"{provider} {operation} failed"

    # Handle standard logging.Logger
    if isinstance(logger, logging.Logger):
        logger.error(message, exc_info=exc_info, extra=context)
    else:
        # Assume structlog or compatible
        logger.error(message, exc_info=exc_info, **context)
