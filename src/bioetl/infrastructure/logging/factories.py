import structlog

from bioetl.infrastructure.logging.contracts import (
    LoggerAdapterABC,
    ProgressReporterABC,
)
from bioetl.infrastructure.logging.impl.progress_reporter import (
    TqdmProgressReporterImpl,
)
from bioetl.infrastructure.logging.impl.unified_logger import UnifiedLoggerImpl


def default_logger() -> LoggerAdapterABC:
    """
    Создает и конфигурирует логгер по умолчанию.
    """
    if not structlog.is_configured():
        structlog.configure(
            processors=[
                structlog.processors.TimeStamper(fmt="iso"),
                structlog.processors.JSONRenderer(),
            ],
            logger_factory=structlog.PrintLoggerFactory(),
        )
    return UnifiedLoggerImpl()


def default_progress_reporter() -> ProgressReporterABC:
    """
    Возвращает репортер прогресса по умолчанию (tqdm).
    """
    return TqdmProgressReporterImpl()
