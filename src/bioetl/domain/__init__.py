"""Domain layer: entities, value objects, and ports."""

from bioetl.domain.types import (
    BatchID,
    CircuitBreakerState,
    ContentHash,
    DataClassification,
    DQStatus,
    DriftLevel,
    EntityID,
    ErrorType,
    HealthStatus,
    RunID,
    RunType,
    Watermark,
)

__all__ = [
    # Type aliases
    "RunID",
    "EntityID",
    "ContentHash",
    "BatchID",
    "Watermark",
    # Enums
    "RunType",
    "DriftLevel",
    "HealthStatus",
    "CircuitBreakerState",
    "DataClassification",
    "ErrorType",
    "DQStatus",
]
