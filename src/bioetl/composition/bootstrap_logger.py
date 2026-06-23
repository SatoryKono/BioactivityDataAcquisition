"""Bootstrap-phase structured logging for composition layer.

Provides structured logging for the composition layer during bootstrap,
before run_id is available. Uses structlog for consistent output format
with pipeline execution logs.

Key differences from pipeline LoggerPort:
- No run_id binding (uses "bootstrap" sentinel)
- stage is always "bootstrap"
- Intended for configuration/registration logging only

Usage:
    from bioetl.composition.bootstrap_logger import get_bootstrap_logger

    logger = get_bootstrap_logger()
    logger.debug("config_loaded", provider="chembl", source="yaml")

Requirements:
- SHOULD: Structured logging in composition layer (audit-2026-01-06)
- REQ-OBS-004: Structured JSON format
"""

from __future__ import annotations

import structlog  # Allowed: composition root configures logging before DI container

from bioetl.infrastructure.observability.logging_config import (
    configure_logging,
    is_logging_configured,
)

# Module-level cached logger instance
_bootstrap_logger: structlog.stdlib.BoundLogger | None = None


def get_bootstrap_logger() -> structlog.stdlib.BoundLogger:
    """Get a structured logger for bootstrap-phase logging.

    Returns a structlog logger pre-bound with bootstrap context:
    - run_id: "bootstrap" (sentinel value, no actual run_id yet)
    - stage: "bootstrap"

    The logger is cached at module level for efficiency.
    Ensures structlog is configured before use.

    Returns:
        Bound structlog logger with bootstrap context.

    Example:
        >>> logger = get_bootstrap_logger()
        >>> logger.debug("source_config_loaded", provider="chembl")
        >>> logger.warning("config_fallback", provider="pubchem", reason="yaml_not_found")
    """
    global _bootstrap_logger

    if _bootstrap_logger is not None:
        return _bootstrap_logger

    # Ensure structlog is configured (idempotent)
    if not is_logging_configured():
        configure_logging(json_format=True, log_level="INFO")

    # Create logger with bootstrap context
    base_logger = structlog.get_logger("bioetl.composition.bootstrap")
    _bootstrap_logger = base_logger.bind(
        run_id="bootstrap",
        stage="bootstrap",
    )

    return _bootstrap_logger


def reset_bootstrap_logger() -> None:
    """Reset the cached bootstrap logger (for testing only).

    Warning:
        This is intended for test fixtures only. Do not use in production code.
    """
    global _bootstrap_logger
    _bootstrap_logger = None


class BootstrapLogger:
    """Wrapper class providing LoggerPort-like interface for bootstrap phase.

    Provides familiar info/debug/warning/error methods while using
    structlog under the hood with bootstrap context pre-bound.

    Example:
        >>> logger = BootstrapLogger()
        >>> logger.debug("loading_config", provider="chembl")
        >>> logger.warning("fallback_defaults", provider="pubchem")
    """

    __slots__ = ("_logger",)

    def __init__(self) -> None:
        """Initialize with the bootstrap logger."""
        self._logger = get_bootstrap_logger()

    def debug(self, event: str, **kwargs: object) -> None:
        """Log a debug message.

        Args:
            event: The event name/message.
            **kwargs: Additional context for the log entry.
        """
        self._logger.debug(event, **kwargs)

    def info(self, event: str, **kwargs: object) -> None:
        """Log an informational message.

        Args:
            event: The event name/message.
            **kwargs: Additional context for the log entry.
        """
        self._logger.info(event, **kwargs)

    def warning(
        self,
        event: str,
        **kwargs: object,
    ) -> None:
        """Log a warning message.

        Args:
            event: The event name/message.
            **kwargs: Additional context for the log entry.
        """
        self._logger.warning(event, **kwargs)

    def error(self, event: str, **kwargs: object) -> None:
        """Log an error message.

        Args:
            event: The event name/message.
            **kwargs: Additional context for the log entry.
        """
        self._logger.error(event, **kwargs)


__all__ = [
    "BootstrapLogger",
    "get_bootstrap_logger",
    "reset_bootstrap_logger",
]
