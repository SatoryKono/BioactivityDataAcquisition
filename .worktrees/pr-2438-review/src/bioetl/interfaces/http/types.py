"""HTTP interface types for BioETL."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class HealthResponse:
    """Health check response data."""

    status: str
    timestamp: str
    version: str = "1.0.0"
    checks: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(
            {
                "status": self.status,
                "timestamp": self.timestamp,
                "version": self.version,
                "checks": self.checks,
            },
            indent=2,
        )

    @property
    def http_status(self) -> int:
        """Return HTTP status code based on health status."""
        if self.status == "healthy":
            return 200
        elif self.status == "degraded":
            return 200  # Still operational
        return 503  # Service Unavailable


__all__ = ["HealthResponse"]
