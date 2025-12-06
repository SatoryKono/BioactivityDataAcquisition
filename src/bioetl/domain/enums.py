from enum import Enum


class ErrorAction(Enum):
    """Действия при ошибке."""

    FAIL = "fail"
    SKIP = "skip"
    RETRY = "retry"
