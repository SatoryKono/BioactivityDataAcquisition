from bioetl.domain.clients.base.logging.contracts import ProgressReporterABC
from bioetl.domain.observability import LoggingPort
from bioetl.infrastructure.logging.impl.progress_reporter import (
    TqdmProgressReporterImpl,
)
from bioetl.infrastructure.observability.factories import default_logging_port


def default_logger() -> LoggingPort:
    """
    Создает и конфигурирует логгер по умолчанию.
    """
    return default_logging_port()


def default_progress_reporter() -> ProgressReporterABC:
    """
    Возвращает репортер прогресса по умолчанию (tqdm).
    """
    return TqdmProgressReporterImpl()
