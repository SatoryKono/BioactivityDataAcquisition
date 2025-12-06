import structlog

from bioetl.domain.clients.base.logging.contracts import ProgressReporterABC
from bioetl.domain.observability import LoggingPort
from bioetl.infrastructure.logging.impl.progress_reporter import (
    TqdmProgressReporterImpl,
)
from bioetl.infrastructure.logging.impl.unified_logger import UnifiedLoggerImpl
from bioetl.infrastructure.observability import factories as observability_factories


def default_logger() -> LoggingPort:
    """
    Создает и конфигурирует логгер по умолчанию.
    """
    observability_factories._configure_structlog()
    return UnifiedLoggerImpl(logger=structlog.get_logger())


def default_progress_reporter() -> ProgressReporterABC:
    """
    Возвращает репортер прогресса по умолчанию (tqdm).
    """
    return TqdmProgressReporterImpl()
