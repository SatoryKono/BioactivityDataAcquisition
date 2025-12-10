"""Consolidated infrastructure settings module.

This module provides unified access to all infrastructure constants,
organized as frozen dataclasses and Enums for type safety.

Modules:
    http: HTTP client settings (timeouts, retries, connection pool)
    files: File operation settings (buffer sizes, temp paths)
    metrics: Prometheus metric names as Enum
"""

from bioetl.infrastructure.settings.files import FileSettings
from bioetl.infrastructure.settings.http import (
    ConnectionPoolSettings,
    HttpTimeouts,
    RetrySettings,
)
from bioetl.infrastructure.settings.metrics import MetricName

__all__ = [
    # HTTP settings
    "HttpTimeouts",
    "RetrySettings",
    "ConnectionPoolSettings",
    # File settings
    "FileSettings",
    # Metric names
    "MetricName",
]
