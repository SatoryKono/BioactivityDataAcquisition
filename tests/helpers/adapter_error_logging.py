"""Test helper for standardized adapter error logging format."""

from __future__ import annotations

from typing import Any, Literal

StageType = Literal["extract", "transform", "load", "validate", "init", "cleanup"]


def log_adapter_error(
    logger: Any,
    provider: str,
    operation: str,
    *,
    stage: StageType = "extract",
    error_type: str = "adapter_error",
    exc_info: bool = True,
    **context: Any,
) -> None:
    """Log adapter error in standardized format with Log Schema fields."""
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
