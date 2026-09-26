"""Telemetry helpers for checkpoint compatibility validation outcomes."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort, MetricsPort

__all__ = [
    "emit_checkpoint_compatibility_metric",
    "log_lenient_checkpoint_compatibility_result",
    "log_strict_checkpoint_compatibility_result",
]


def emit_checkpoint_compatibility_metric(
    metrics: MetricsPort | None,
    *,
    pipeline_name: str | None,
    disposition: str,
) -> None:
    """Emit one checkpoint compatibility event metric when metrics are enabled."""
    if metrics is None:
        return
    metrics.increment_counter(
        "bioetl_checkpoint_compatibility_events_total",
        1,
        {
            "pipeline": pipeline_name or "unknown",
            "disposition": disposition,
        },
    )


def log_strict_checkpoint_compatibility_result(
    logger: LoggerPort,
    *,
    compatible: bool,
    messages: list[str],
) -> None:
    """Log the outcome of a strict checkpoint compatibility check."""
    if compatible:
        logger.info(
            "Checkpoint compatibility validation passed",
            messages=messages,
        )
        return
    logger.warning(
        "Checkpoint compatibility validation failed",
        messages=messages,
    )


def log_lenient_checkpoint_compatibility_result(
    logger: LoggerPort,
    *,
    compatible: bool,
    messages: list[str],
) -> None:
    """Log the outcome of a lenient checkpoint compatibility check."""
    if compatible:
        logger.info(
            "Checkpoint minimum compatibility validation passed (lenient mode)",
            messages=messages,
        )
        return
    logger.warning(
        "Checkpoint minimum compatibility validation failed (lenient mode)",
        messages=messages,
    )
