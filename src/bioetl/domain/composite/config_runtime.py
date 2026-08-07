"""Runtime-related composite configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field

from bioetl.domain.immutability import freeze_fields

__all__ = [
    "ExecutionConfig",
    "LineageConfig",
]


@dataclass(frozen=True, slots=True)
class ExecutionConfig:
    """Execution options for composite pipeline.

    Attributes:
        max_concurrency: Maximum concurrent enrichers.
        checkpoint_enabled: Enable checkpointing for resume.
        retry_max_attempts: Max retry attempts per enricher.
        retry_backoff_multiplier: Backoff multiplier for retries.
    """

    max_concurrency: int = 4
    checkpoint_enabled: bool = True
    retry_max_attempts: int = 3
    retry_backoff_multiplier: float = 2.0

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.max_concurrency <= 0:
            raise ValueError(
                f"max_concurrency must be positive, got {self.max_concurrency}"
            )
        if self.retry_max_attempts < 0:
            raise ValueError(
                f"retry_max_attempts must be non-negative, got {self.retry_max_attempts}"
            )
        if self.retry_backoff_multiplier <= 0:
            raise ValueError(
                f"retry_backoff_multiplier must be positive, got {self.retry_backoff_multiplier}"
            )


@dataclass(frozen=True, slots=True)
class LineageConfig:
    """Configuration for lineage tracking.

    Attributes:
        track_field_sources: Track which source provided each field.
        track_timestamps: Include enrichment timestamps.
        track_status: Include per-record enrichment status.
        provider_lookup_fields: Per-provider mapping of lookup metadata field names.
        track_source_for_fields: Field names requiring source tracking for overlapping data.
    """

    track_field_sources: bool = True
    track_timestamps: bool = True
    track_status: bool = True
    provider_lookup_fields: dict[str, dict[str, str]] = field(default_factory=dict)
    track_source_for_fields: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        """Freeze nested mappings/sequences so callers cannot mutate state."""
        if isinstance(self.track_source_for_fields, list):
            object.__setattr__(
                self, "track_source_for_fields", tuple(self.track_source_for_fields)
            )
        freeze_fields(self, ("provider_lookup_fields",))
