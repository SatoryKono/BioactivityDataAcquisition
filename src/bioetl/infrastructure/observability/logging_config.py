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
import os
import re
import sys
import threading
from pathlib import Path
from typing import Any

import structlog

from bioetl.domain.types import JsonDict

# Thread-safe configuration state
_config_lock = threading.Lock()
_configured = False
_current_format: bool | None = None  # True = JSON, False = Console
_DEFAULT_LOG_FILE = Path("logs") / "bioetl.log"

# Patterns for secret detection in log values
_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"(?i)(api[_-]?key)['\"]?\s*[:=]\s*['\"]?[\w-]+", re.IGNORECASE),
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

# UUID pattern used to avoid redacting identifiers like run_id, batch_id
_UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$",
    re.IGNORECASE,
)


def _mask_secrets(value: Any) -> Any:  # Any: structlog context values of arbitrary type
    """Mask potential secrets in log values.

    Preserves UUID-format strings (used as run_id, batch_id, etc.)
    while redacting actual secrets like API keys and tokens.

    Args:
        value: Value to check and potentially mask

    Returns:
        Original value or masked version if secrets detected
    """
    if not isinstance(value, str):
        return value

    # Preserve UUID-format identifiers (run_id, batch_id, content_hash)
    if _UUID_PATTERN.match(value):
        return value

    result = value
    for pattern, replacement in _SECRET_PATTERNS:
        result = pattern.sub(replacement, result)

    return result


def secret_filter_processor(
    logger: Any,  # Any: structlog wrapped logger instance
    _method_name: str,
    event_dict: JsonDict,  # Any: OTel span attributes are heterogeneous
) -> JsonDict:  # Any: OTel span attributes are heterogeneous
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


def _get_current_trace_identifiers() -> tuple[str, str] | None:
    """Return current OTel trace/span identifiers when an active span exists."""
    try:
        from opentelemetry import trace as otel_trace
    except ImportError:
        return None

    try:
        current_span = otel_trace.get_current_span()
        if current_span is None:
            return None
        span_context = current_span.get_span_context()
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None

    trace_id = getattr(span_context, "trace_id", 0)
    span_id = getattr(span_context, "span_id", 0)
    is_valid = getattr(span_context, "is_valid", None)

    if is_valid is False:
        return None
    if not isinstance(trace_id, int) or not isinstance(span_id, int):
        return None
    if trace_id <= 0 or span_id <= 0:
        return None

    return (f"{trace_id:032x}", f"{span_id:016x}")


def trace_context_processor(
    _logger: object,
    _method_name: str,
    event_dict: JsonDict,
) -> JsonDict:
    """Attach current trace correlation fields to the structured log event."""
    trace_identifiers = _get_current_trace_identifiers()
    if trace_identifiers is None:
        return event_dict

    trace_id, span_id = trace_identifiers
    event_dict.setdefault("trace_id", trace_id)
    event_dict.setdefault("span_id", span_id)
    return event_dict


def _resolve_log_file_path() -> Path | None:
    """Resolve the effective file sink path for runtime logging.

    Resolution order:
    1. ``BIOETL_LOG_FILE`` explicit override
    2. no default file sink during pytest runs
    3. repository-local ``logs/bioetl.log`` for normal runtime usage
    """
    configured_path = os.getenv("BIOETL_LOG_FILE")
    if configured_path is not None:
        normalized = configured_path.strip()
        if not normalized:
            return None
        return Path(normalized)

    if os.getenv("PYTEST_CURRENT_TEST"):
        return None

    return _DEFAULT_LOG_FILE


def _build_shared_processors() -> list[
    Any
]:  # Any: structlog processors have heterogeneous callable signatures.
    """Build processors shared by structlog and foreign stdlib loggers."""
    return [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
        trace_context_processor,
        secret_filter_processor,
    ]


def configure_logging(
    json_format: bool = True,
    log_level: str = "INFO",
    *,
    force: bool = False,
) -> bool:
    """Configure global structlog/stdlib logging; optionally force reconfiguration.

    Returns:
        True if logging was configured, False if already configured and force=False.
    """
    global _configured, _current_format

    with _config_lock:
        if _configured and not force:
            return False

        shared_processors = _build_shared_processors()
        renderer: Any = (  # Any: renderer may be JSONRenderer or ConsoleRenderer with different concrete types.
            structlog.processors.JSONRenderer()
            if json_format
            else structlog.dev.ConsoleRenderer()
        )

        structlog.configure(
            processors=[
                *shared_processors,
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                renderer,
            ],
        )

        handlers: list[logging.Handler] = [logging.StreamHandler(sys.stdout)]
        log_path = _resolve_log_file_path()
        if log_path is not None:
            log_path.parent.mkdir(parents=True, exist_ok=True)
            handlers.append(logging.FileHandler(log_path, encoding="utf-8"))
        for handler in handlers:
            handler.setFormatter(formatter)

        logging.basicConfig(
            level=log_level.upper(),
            format="%(message)s",
            handlers=handlers,
            force=True,
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
    """Reset the logging configuration state.

    ONLY FOR USE IN TESTS. Resets internal state to allow configure_logging()
    to be called again. Note that structlog.configure() itself cannot be
    fully undone, but this allows re-calling our configuration wrapper.
    """
    global _configured, _current_format
    with _config_lock:
        logging.shutdown()
        root_logger = logging.getLogger()
        for handler in list(root_logger.handlers):
            root_logger.removeHandler(handler)
        _configured = False
        _current_format = None


__all__ = [
    "configure_logging",
    "is_logging_configured",
    "reset_logging_config",
    "secret_filter_processor",
    "trace_context_processor",
]
