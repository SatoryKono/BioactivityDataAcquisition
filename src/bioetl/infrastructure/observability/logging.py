"""Structured logging implementation for BioETL.

Implements RULES.md §3.2 - Log Schema with mandatory fields:
- ts: ISO timestamp
- level: log level
- run_id: correlation ID (UUID)
- pipeline: pipeline name
- stage: extract | transform | load
- dataset: logical table name (SHOULD)
- record_count: count of records (SHOULD)

Requirements:
- REQ-OBS-001: run_id mandatory in all logs
- REQ-OBS-004: Structured JSON format
- REQ-OBS-005: Log Schema with mandatory fields
"""

from __future__ import annotations

import logging
import sys
from typing import Any
from uuid import UUID

import structlog


def create_logger(
    pipeline: str,
    run_id: UUID,
    log_level: str = "INFO",
    json_format: bool = True,
) -> Any:
    """Create a structured logger factory.

    Args:
        pipeline: Pipeline name for log context.
        run_id: Unique run identifier for tracing.
        log_level: Logging level (default: INFO).
        json_format: Use JSON output format (default: True).

    Returns:
        Configured structlog logger with bound context.

    """
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
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

    logger = structlog.get_logger(f"bioetl.{pipeline}")
    logger = logger.bind(run_id=str(run_id), pipeline=pipeline)

    # Set the log level for the underlying standard logger
    logging.basicConfig(
        level=log_level.upper(),
        stream=sys.stdout,
        format="%(message)s",
    )

    return logger
