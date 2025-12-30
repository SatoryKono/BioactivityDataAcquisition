"""Centralized structlog configuration for BioETL.

This module provides a single point of configuration for structlog
to avoid repeated calls to structlog.configure() which can cause
configuration conflicts when multiple loggers are created.

Usage:
    # At application startup (e.g., in bootstrap.py or CLI):
    from bioetl.infrastructure.observability.logging_config import configure_logging
    configure_logging(json_format=True, log_level="INFO")

    # Then create loggers normally:
    from bioetl.infrastructure.observability.unified_logger import UnifiedLogger
    logger = UnifiedLogger(pipeline="chembl", run_id="abc-123")

Requirements:
- REQ-OBS-004: Structured JSON format
- REQ-OBS-005: Log Schema with mandatory fields
"""

from __future__ import annotations

import logging
import re
import sys
import threading
from typing import Any

import structlog

# Thread-safe configuration state
_config_lock = threading.Lock()
_configured = False
_current_format: bool | None = None  # True = JSON, False = Console


# Patterns for secret detection in log values
_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(
            r"(?i)(api[_-]?key|apikey)['\"]?\s*[:=]\s*['\"]?[\w-]+", re.IGNORECASE
        ),
        "[REDACTED_API_KEY]",
    ),
    (
        re.compile(
            r"(?i)(auth|authorization)['\"]?\s*[:=]\s*['\"]?[\w-]+", re.IGNORECASE
        ),
        "[REDACTED_AUTH]",
    ),
    (
        re.compile(r"(?i)(token|bearer)['\"]?\s*[:=]\s*['\"]?[\w-]+", re.IGNORECASE),
        "[REDACTED_TOKEN]",
    ),
    (
        re.compile(
            r"(?i)(password|passwd|pwd)['\"]?\s*[:=]\s*['\"]?[\w-]+", re.IGNORECASE
        ),
        "[REDACTED_PASSWORD]",
    ),
    (
        re.compile(
            r"(?i)(secret|private[_-]?key)['\"]?\s*[:=]\s*['\"]?[\w-]+", re.IGNORECASE
        ),
        "[REDACTED_SECRET]",
    ),
    # Bearer tokens in headers
    (re.compile(r"Bearer\s+[\w.-]+", re.IGNORECASE), "Bearer [REDACTED]"),
    # AWS-style keys
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED_AWS_KEY]"),
    # Generic long alphanumeric that look like keys (32+ chars)
    (re.compile(r"(?<![a-zA-Z0-9])[a-zA-Z0-9]{32,}(?![a-zA-Z0-9])"), "[REDACTED_KEY]"),
]


def _mask_secrets(value: Any) -> Any:
    """Mask potential secrets in log values.

    Args:
        value: Value to check and potentially mask

    Returns:
        Original value or masked version if secrets detected
    """
    if not isinstance(value, str):
        return value

    result = value
    for pattern, replacement in _SECRET_PATTERNS:
        result = pattern.sub(replacement, result)

    return result


def secret_filter_processor(
    logger: Any,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """Structlog processor that filters secrets from log entries.

    Scans all string values in the event dict and masks potential secrets
    like API keys, tokens, passwords, and authorization headers.

    Args:
        logger: The wrapped logger object
        _method_name: Name of the log method called
        event_dict: Dictionary of event data

    Returns:
        Event dict with secrets masked
    """
    for key, value in event_dict.items():
        if isinstance(value, str):
            event_dict[key] = _mask_secrets(value)
        elif isinstance(value, dict):
            # Recursively mask nested dicts
            event_dict[key] = {
                k: _mask_secrets(v) if isinstance(v, str) else v
                for k, v in value.items()
            }

    return event_dict


def configure_logging(
    json_format: bool = True,
    log_level: str = "INFO",
    *,
    force: bool = False,
) -> bool:
    """Configure structlog globally for the application.

    This function should be called once at application startup.
    Subsequent calls are no-ops unless force=True.

    Args:
        json_format: Use JSON output format (default: True)
        log_level: Logging level (default: INFO)
        force: Force reconfiguration even if already configured

    Returns:
        True if configuration was applied, False if already configured
    """
    global _configured, _current_format

    with _config_lock:
        if _configured and not force:
            # Already configured - check if format matches
            if _current_format != json_format:
                # Format mismatch - log warning but don't reconfigure
                # This prevents issues with multiple loggers requesting different formats
                pass
            return False

        # Build processor chain with secret filtering
        processors: list[Any] = [
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            secret_filter_processor,  # Filter secrets before output
        ]

        if json_format:
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer())

        structlog.configure(
            processors=processors,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        # Configure stdlib logging level
        logging.basicConfig(
            level=log_level.upper(),
            stream=sys.stdout,
            format="%(message)s",
            force=True,  # Override any existing configuration
        )

        _configured = True
        _current_format = json_format
        return True


def is_logging_configured() -> bool:
    """Check if logging has been configured.

    Returns:
        True if configure_logging() has been called
    """
    with _config_lock:
        return _configured


def reset_logging_config() -> None:
    """Reset logging configuration state (for testing only).

    Warning:
        This is intended for test fixtures only. Do not use in production code.
    """
    global _configured, _current_format
    with _config_lock:
        _configured = False
        _current_format = None


__all__ = [
    "configure_logging",
    "is_logging_configured",
    "reset_logging_config",
    "secret_filter_processor",
]
