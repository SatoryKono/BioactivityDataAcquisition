from __future__ import annotations

"""Error types for consistent error handling across the application."""

from enum import Enum


class ErrorType(Enum):
    """Enumeration of error types."""

    VALIDATION_ERROR = "validation_error"
    NETWORK_ERROR = "network_error"
    STORAGE_ERROR = "storage_error"
    CONFIGURATION_ERROR = "configuration_error"
    UNKNOWN_ERROR = "unknown_error"
    INFRASTRUCTURE_ERROR = "infrastructure_error"
    DATA_QUALITY_ERROR = "data_quality_error"
    INVALID_DATA = "invalid_data"
