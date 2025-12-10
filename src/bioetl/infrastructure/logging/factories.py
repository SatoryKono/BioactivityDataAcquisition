"""Factories for structured logging adapters and progress reporters."""

import structlog

from bioetl.domain.observability import LoggingPortABC, ProgressReporterABC
from bioetl.infrastructure.logging.impl.progress_reporter import (
    TqdmProgressReporterImpl,
)
from bioetl.infrastructure.observability import factories as observability_factories
from bioetl.infrastructure.observability.adapters import StructuredLoggerImpl


def default_logger() -> LoggingPortABC:
    """
    Создает и конфигурирует логгер по умолчанию.
    """
    observability_factories._configure_structlog()
    return StructuredLoggerImpl(logger=structlog.get_logger())


def default_progress_reporter() -> ProgressReporterABC:
    """
    Возвращает репортер прогресса по умолчанию (tqdm).
    """
    return TqdmProgressReporterImpl()
