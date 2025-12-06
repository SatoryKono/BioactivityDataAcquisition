from typing import Any, Self

from typing import Any, Self

import structlog
from structlog.stdlib import BoundLogger

from bioetl.domain.observability import LoggingPort


class UnifiedLoggerImpl(LoggingPort):
    """
    Реализация логгера на основе structlog.
    """

    def __init__(self, logger: BoundLogger | None = None) -> None:
        self._logger = logger or structlog.get_logger()

    def info(self, msg: str, **ctx: Any) -> None:
        self._logger.info(msg, **ctx)

    def error(self, msg: str, **ctx: Any) -> None:
        self._logger.error(msg, **ctx)

    def debug(self, msg: str, **ctx: Any) -> None:
        self._logger.debug(msg, **ctx)

    def warning(self, msg: str, **ctx: Any) -> None:
        self._logger.warning(msg, **ctx)

    def bind(self, **ctx: Any) -> Self:
        return self.__class__(self._logger.bind(**ctx))
