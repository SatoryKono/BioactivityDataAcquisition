"""Domain context objects.

Provides context objects for pipeline execution with strict typing:
- PipelineContext: Runtime context for pipeline components
- PipelineRunContext: Full launch parameters from CLI/Orchestrator
- InputFilterContext: Optional filter configuration for input-based filtering
- VacuumConfig: Vacuum operation settings with explicit defaults
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import RunID, RunType

# Backward compatibility alias
BoundLogger = LoggerPort


def _now_utc() -> datetime:
    """Factory function for default started_at timestamp."""
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class InputFilterContext:
    """Input filter configuration for CSV-based ID filtering.

    All fields are required when filtering is enabled.
    Create via InputFilterContext.from_cli_args() or InputFilterContext.disabled().
    """

    enabled: bool
    source_path: str
    column_name: str
    filter_field: str

    @classmethod
    def disabled(cls) -> InputFilterContext:
        """Create a disabled filter context."""
        return cls(
            enabled=False,
            source_path="",
            column_name="",
            filter_field="",
        )

    @classmethod
    def from_csv(
        cls, source_path: str, column_name: str, filter_field: str
    ) -> InputFilterContext:
        """Create an enabled filter context from CSV parameters."""
        return cls(
            enabled=True,
            source_path=source_path,
            column_name=column_name,
            filter_field=filter_field,
        )

    def __post_init__(self) -> None:
        """Validate filter configuration."""
        if self.enabled:
            if not self.source_path:
                raise ValueError("source_path is required when filter is enabled")
            if not self.column_name:
                raise ValueError("column_name is required when filter is enabled")
            if not self.filter_field:
                raise ValueError("filter_field is required when filter is enabled")


@dataclass(frozen=True, slots=True)
class VacuumConfig:
    """Vacuum operation configuration with explicit defaults.

    Provides non-optional configuration for vacuum operations.
    """

    enabled: bool = False
    retention_days: int = 7

    def __post_init__(self) -> None:
        """Validate vacuum configuration."""
        if self.retention_days <= 0:
            raise ValueError(
                f"retention_days must be positive, got {self.retention_days}"
            )


@dataclass(frozen=True, slots=True)
class PipelineContext:
    """Context object for a pipeline run.

    Provides a consistent set of metadata to all pipeline components.
    The started_at field is the single source of truth for timestamps
    within a pipeline run (see ADR-014).
    """

    run_id: RunID
    run_type: RunType
    logger: LoggerPort
    started_at: datetime = field(default_factory=_now_utc)

    @classmethod
    def create(
        cls,
        run_id: RunID,
        run_type: RunType,
        logger: LoggerPort,
        started_at: datetime | None = None,
    ) -> PipelineContext:
        """Create a new PipelineContext with optional automatic timestamp.

        Args:
            run_id: Unique identifier for the pipeline run
            run_type: Type of run (incremental, backfill, rebuild)
            logger: Structured logger for observability
            started_at: Optional timestamp; if None, uses current UTC time

        Returns:
            New PipelineContext instance
        """
        return cls(
            run_id=run_id,
            run_type=run_type,
            logger=logger,
            started_at=started_at or datetime.now(UTC),
        )

    def bind_logger(self, **kwargs: Any) -> PipelineContext:
        """Bind additional context to the logger.

        Returns a new context with the bound logger.
        """
        new_logger = self.logger.bind(**kwargs)
        return PipelineContext(
            run_id=self.run_id,
            run_type=self.run_type,
            logger=new_logger,
            started_at=self.started_at,
        )


@dataclass(frozen=True, slots=True)
class PipelineRunContext:
    """Context object encapsulating pipeline launch parameters.

    Used to pass runtime arguments from CLI/Orchestrator to the Composition Root.

    Design: Fields are split into required, defaulted, and optional categories:
    - Required: pipeline_name, run_id, run_type (no defaults)
    - Defaulted: resume, dry_run, vacuum, input_filter (explicit defaults, not None)
    - Optional: limit, query (truly optional runtime overrides)
    """

    # Required fields (no defaults)
    pipeline_name: str
    run_id: RunID
    run_type: RunType

    # Defaulted fields (explicit non-None defaults)
    resume: bool = False
    dry_run: bool = False
    vacuum: VacuumConfig = field(default_factory=VacuumConfig)
    input_filter: InputFilterContext = field(default_factory=InputFilterContext.disabled)

    # Truly optional fields (None means "not specified, use config default")
    limit: int | None = None
    query: str | None = None

    # DEPRECATED: Legacy fields for backward compatibility
    # TODO: Remove in v2.0 after migration to InputFilterContext
    input_csv: str | None = None
    filter_column: str | None = None
    filter_field: str | None = None
    vacuum_after_run: bool | None = None
    vacuum_retention_days: int | None = None

    def __post_init__(self) -> None:
        """Validate context and migrate legacy fields."""
        # Migrate legacy input filter fields to InputFilterContext
        if any([self.input_csv, self.filter_column, self.filter_field]):
            if self.input_filter.enabled:
                # Both new and legacy specified - use new
                pass
            elif self.input_csv and self.filter_column and self.filter_field:
                # All legacy fields present - create filter context
                new_filter = InputFilterContext.from_csv(
                    source_path=self.input_csv,
                    column_name=self.filter_column,
                    filter_field=self.filter_field,
                )
                object.__setattr__(self, "input_filter", new_filter)

        # Migrate legacy vacuum fields to VacuumConfig
        if self.vacuum_after_run is not None or self.vacuum_retention_days is not None:
            if not self.vacuum.enabled:  # Only migrate if new config not set
                new_vacuum = VacuumConfig(
                    enabled=self.vacuum_after_run or False,
                    retention_days=self.vacuum_retention_days or 7,
                )
                object.__setattr__(self, "vacuum", new_vacuum)

    @property
    def has_input_filter(self) -> bool:
        """Check if input filtering is enabled."""
        return self.input_filter.enabled

    @property
    def vacuum_enabled(self) -> bool:
        """Check if vacuum is enabled (backward compatible)."""
        return self.vacuum.enabled
