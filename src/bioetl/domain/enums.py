"""Common enumerations used across BioETL domain."""

from enum import Enum


class ErrorAction(Enum):
    """Error handling actions."""

    FAIL = "fail"
    SKIP = "skip"
    RETRY = "retry"
