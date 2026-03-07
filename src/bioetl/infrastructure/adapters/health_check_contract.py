"""Shared types/constants for adapter health-check mixins."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from httpx import HTTPStatusError, RequestError

from bioetl.domain.exceptions import BioETLError, NetworkError

HEALTH_CHECK_ERRORS = (
    BioETLError,
    NetworkError,
    RequestError,
    HTTPStatusError,
    ConnectionError,
    TimeoutError,
    OSError,
    ValueError,
    TypeError,
    RuntimeError,
    AttributeError,
    Exception,
)


@dataclass
class HealthCheckContext:
    """Context for health check operations."""

    start_time: float = field(default_factory=time.monotonic)
    provider: str = ""
    endpoint: str = ""

    @property
    def elapsed_seconds(self) -> float:
        """Calculate elapsed time since start."""
        return time.monotonic() - self.start_time
