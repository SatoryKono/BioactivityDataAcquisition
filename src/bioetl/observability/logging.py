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

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class LogRecord(BaseModel):
    """Structured log record conforming to RULES.md Log Schema.

    See RULES.md §3.2.1 for complete specification.
    """

    ts: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    level: str  # INFO, WARNING, ERROR, CRITICAL
    run_id: UUID  # Correlation ID (MUST)
    pipeline: str  # Pipeline name (MUST)
    stage: str  # extract | transform | load (MUST)
    message: str
    dataset: str | None = None  # Logical table name (SHOULD)
    record_count: int | None = None  # Record count (SHOULD)
    error_type: str | None = None  # Error classification
    error_details: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_json(self) -> str:
        """Convert to JSON string for structured logging."""
        data = self.model_dump(mode="json", exclude_none=True)
        data["ts"] = self.ts.isoformat()
        data["run_id"] = str(self.run_id)
        return json.dumps(data, separators=(",", ":"), ensure_ascii=True)


class StructuredLogger:
    """Structured logger with correlation ID tracking.

    Usage:
        logger = StructuredLogger(
            pipeline="chembl_activity",
            run_id=UUID("..."),
            log_file=Path("logs/bioetl.log")
        )

        logger.info("Extraction started", stage="extract", record_count=1000)
        logger.error("Validation failed", stage="transform", error_type="SCHEMA_VIOLATION")
    """

    def __init__(
        self,
        pipeline: str,
        run_id: UUID,
        log_file: Path | None = None,
        log_level: str = "INFO",
        json_format: bool = True,
    ):
        self.pipeline = pipeline
        self.run_id = run_id
        self.json_format = json_format

        # Create Python logger
        self._logger = logging.getLogger(f"bioetl.{pipeline}")
        self._logger.setLevel(getattr(logging, log_level.upper()))
        self._logger.handlers.clear()  # Clear any existing handlers

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        self._logger.addHandler(console_handler)

        # File handler (if specified)
        if log_file:
            log_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(getattr(logging, log_level.upper()))
            self._logger.addHandler(file_handler)

    def _log(
        self,
        level: str,
        message: str,
        stage: str,
        dataset: str | None = None,
        record_count: int | None = None,
        error_type: str | None = None,
        error_details: dict[str, Any] | None = None,
        **metadata: Any,
    ) -> None:
        """Internal logging method."""
        record = LogRecord(
            level=level.upper(),
            run_id=self.run_id,
            pipeline=self.pipeline,
            stage=stage,
            message=message,
            dataset=dataset,
            record_count=record_count,
            error_type=error_type,
            error_details=error_details,
            metadata=metadata,
        )

        if self.json_format:
            log_message = record.to_json()
        else:
            # Human-readable format for development
            log_message = (
                f"[{record.ts.isoformat()}] {record.level} | "
                f"{record.pipeline}:{record.stage} | {record.message}"
            )
            if record.record_count:
                log_message += f" | records={record.record_count}"

        # Log to Python logger
        self._logger.log(getattr(logging, level.upper()), log_message)

    def info(
        self,
        message: str,
        stage: str,
        dataset: str | None = None,
        record_count: int | None = None,
        **metadata: Any,
    ) -> None:
        """Log INFO level message."""
        self._log("INFO", message, stage, dataset, record_count, **metadata)

    def warning(
        self,
        message: str,
        stage: str,
        dataset: str | None = None,
        error_type: str | None = None,
        **metadata: Any,
    ) -> None:
        """Log WARNING level message."""
        self._log("WARNING", message, stage, dataset, error_type=error_type, **metadata)

    def error(
        self,
        message: str,
        stage: str,
        error_type: str,
        error_details: dict[str, Any] | None = None,
        dataset: str | None = None,
        **metadata: Any,
    ) -> None:
        """Log ERROR level message."""
        self._log(
            "ERROR",
            message,
            stage,
            dataset,
            error_type=error_type,
            error_details=error_details,
            **metadata,
        )

    def critical(
        self,
        message: str,
        stage: str,
        error_type: str,
        error_details: dict[str, Any] | None = None,
        **metadata: Any,
    ) -> None:
        """Log CRITICAL level message."""
        self._log(
            "CRITICAL",
            message,
            stage,
            error_type=error_type,
            error_details=error_details,
            **metadata,
        )


def create_logger(
    pipeline: str,
    run_id: UUID,
    log_file: Path | None = None,
    log_level: str = "INFO",
    json_format: bool = True,
) -> StructuredLogger:
    """Factory function to create a structured logger.

    Args:
        pipeline: Pipeline name
        run_id: Correlation ID (UUID)
        log_file: Optional log file path
        log_level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_format: Use JSON format (True) or human-readable (False)

    Returns:
        Configured StructuredLogger instance

    Example:
        >>> from uuid import uuid4
        >>> logger = create_logger(
        ...     pipeline="chembl_activity",
        ...     run_id=uuid4(),
        ...     log_file=Path("logs/bioetl.log")
        ... )
        >>> logger.info("Processing started", stage="extract", record_count=1000)
    """
    return StructuredLogger(
        pipeline=pipeline,
        run_id=run_id,
        log_file=log_file,
        log_level=log_level,
        json_format=json_format,
    )
