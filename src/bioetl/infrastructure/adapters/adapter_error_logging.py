"""Logging utilities for adapters.

Provides standardized error logging format across all data source adapters.
Implements RULES.md §3.2.1 Log Schema with mandatory stage field.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort

# Stage type for Log Schema compliance
StageType = Literal["extract", "transform", "load", "validate", "init", "cleanup"]


def log_adapter_error(
    logger: LoggerPort,
    provider: str,
    operation: str,
    *,
    stage: StageType = "extract",
    error_type: str = "adapter_error",
    exc_info: bool = True,
    **context: Any,
) -> None:
    """Log adapter error in standardized format with Log Schema fields.

    Формат сообщения: "{provider} {operation} failed"

    Implements RULES.md §3.2.1 - mandatory fields:
    - stage: Pipeline stage (default: "extract" for adapter operations)
    - error_type: Error classification

    Args:
        logger: LoggerPort-compatible logger instance
        provider: Provider name (e.g., "chembl", "pubchem", "uniprot")
        operation: Operation that failed (e.g., "fetch", "batch fetch", "health check")
        stage: Pipeline stage for Log Schema (default: "extract")
        error_type: Classification of error (default: "adapter_error")
        exc_info: Include exception traceback (default: True)
        **context: Additional context fields to include in log

    """
    message = f"{provider} {operation} failed"

    logger.error(
        message,
        stage=stage,
        error_type=error_type,
        provider=provider,
        operation=operation,
        exc_info=exc_info,
        **context,
    )
