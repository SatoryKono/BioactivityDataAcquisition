"""Shared types/constants for adapter health-check mixins."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from bioetl.infrastructure.adapters.common.error_bundles import (
    COMMON_ADAPTER_HEALTH_ERRORS_WITH_KEYERROR,
)

HEALTH_CHECK_ERRORS = COMMON_ADAPTER_HEALTH_ERRORS_WITH_KEYERROR


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
