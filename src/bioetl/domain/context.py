"""Domain context objects.

Provides context objects for pipeline execution with strict typing:
- PipelineContext: Runtime context for pipeline components
- PipelineRunContext: Full launch parameters from CLI/Orchestrator
- InputFilterContext: Optional filter configuration for input-based filtering
- VacuumConfig: Vacuum operation settings with explicit defaults
- CachedBronzeContext: Configuration for loading from cached Bronze layer
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from bioetl.domain.ports import LoggerPort
from bioetl.domain.types import RunID, RunType


def _now_utc() -> datetime:
    """Factory function for default started_at timestamp."""
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class CachedBronzeContext:
    """Configuration for loading data from cached Bronze layer.

    When enabled, the pipeline reads from existing Bronze files instead of
    making API calls. This is useful for re-processing without network access
    or for testing transformations on previously fetched data.

    Attributes:
        enabled: Whether to use cached Bronze data instead of API.
        bronze_path: Explicit path to Bronze cache directory. If None,
            uses convention-based path: data/output/bronze/{provider}/{entity}.
        bronze_date: Optional date filter in YYYY-MM-DD format. When set,
            only reads batches from that specific date directory.

    Example:
        >>> # Disabled (default - use API)
        >>> ctx = CachedBronzeContext.disabled()

        >>> # Enabled with convention-based path
        >>> ctx = CachedBronzeContext.from_options(path=None, date=None)

        >>> # Enabled with specific date
        >>> ctx = CachedBronzeContext.from_options(path=None, date="2026-01-20")

        >>> # Enabled with explicit path
        >>> ctx = CachedBronzeContext.from_options(
        ...     path="./data/output/bronze/chembl/activity",
        ...     date="2026-01-20"
        ... )
    """

    enabled: bool = False
    bronze_path: str | None = None
    bronze_date: str | None = None

    @classmethod
    def disabled(cls) -> CachedBronzeContext:
        """Create a disabled context (use API, not cache)."""
        return cls(enabled=False, bronze_path=None, bronze_date=None)

    @classmethod
    def from_options(
        cls,
        path: str | None = None,
        date: str | None = None,
    ) -> CachedBronzeContext:
        """Create an enabled context from CLI/config options.

        Args:
            path: Explicit Bronze cache path, or None to use convention.
            date: Optional date filter in YYYY-MM-DD format.

        Returns:
            Enabled CachedBronzeContext.
        """
        return cls(enabled=True, bronze_path=path, bronze_date=date)

    def __post_init__(self) -> None:
        """Validate cached bronze configuration."""
        if not self.enabled:
            return
        # Validate date format if provided
        if self.bronze_date is not None:
            self._validate_date_format()

    def _validate_date_format(self) -> None:
        """Validate bronze_date is in YYYY-MM-DD format."""
        if self.bronze_date is None:
            return
        try:
            datetime.strptime(self.bronze_date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"bronze_date must be in YYYY-MM-DD format, got '{self.bronze_date}'"
            ) from e


@dataclass(frozen=True, slots=True)
class InputFilterContext:
    """Input filter configuration for CSV-based or direct ID filtering.

    All fields are required when filtering is enabled via CSV.
    For direct IDs, only filter_ids and filter_field are required.
    For multi-field IDs, use multi_filter_ids (dict of field -> IDs).
    Create via InputFilterContext.from_csv(), from_ids(), from_multi_ids(),
    or disabled().
    """

    enabled: bool
    source_path: str
    column_name: str
    filter_field: str
    filter_ids: tuple[str, ...] | None = None
    multi_filter_ids: dict[str, tuple[str, ...]] | None = None
    valid_combinations: frozenset[tuple[str, ...]] | None = None
    fallback_mapping: dict[str, str] | None = None
    fallback_column: str | None = None

    @classmethod
    def disabled(cls) -> InputFilterContext:
        """Create a disabled filter context."""
        return cls(
            enabled=False,
            source_path="",
            column_name="",
            filter_field="",
            filter_ids=None,
            multi_filter_ids=None,
            valid_combinations=None,
            fallback_mapping=None,
            fallback_column=None,
        )

    @classmethod
    def from_csv(
        cls,
        source_path: str,
        column_name: str,
        filter_field: str,
        fallback_column: str | None = None,
    ) -> InputFilterContext:
        """Create an enabled filter context from CSV parameters."""
        return cls(
            enabled=True,
            source_path=source_path,
            column_name=column_name,
            filter_field=filter_field,
            filter_ids=None,
            multi_filter_ids=None,
            valid_combinations=None,
            fallback_mapping=None,
            fallback_column=fallback_column,
        )

    @classmethod
    def from_ids(
        cls,
        filter_ids: tuple[str, ...],
        filter_field: str,
        fallback_mapping: dict[str, str] | None = None,
    ) -> InputFilterContext:
        """Create an enabled filter context from direct IDs.

        Used for composite mode where IDs are passed directly without CSV file.
        """
        return cls(
            enabled=True,
            source_path="",
            column_name="",
            filter_field=filter_field,
            filter_ids=filter_ids,
            multi_filter_ids=None,
            valid_combinations=None,
            fallback_mapping=fallback_mapping,
            fallback_column=None,
        )

    @classmethod
    def from_multi_ids(
        cls,
        multi_filter_ids: dict[str, tuple[str, ...]],
        valid_combinations: frozenset[tuple[str, ...]] | None = None,
    ) -> InputFilterContext:
        """Create an enabled filter context from multi-field IDs.

        Used for composite dependencies that filter by multiple fields
        simultaneously (AND logic). E.g., compound_record filtered by both
        molecule_chembl_id and document_chembl_id.

        Args:
            multi_filter_ids: Mapping of field name to tuple of IDs.
            valid_combinations: Optional set of valid (field1, field2, ...)
                tuples for client-side combination filtering.
        """
        fields = list(multi_filter_ids.keys())
        return cls(
            enabled=True,
            source_path="",
            column_name="",
            filter_field=fields[0] if fields else "",
            filter_ids=None,
            multi_filter_ids=multi_filter_ids,
            valid_combinations=valid_combinations,
            fallback_mapping=None,
            fallback_column=None,
        )

    def __post_init__(self) -> None:
        """Validate filter configuration."""
        if not self.enabled:
            return
        if self.multi_filter_ids is not None:
            self._validate_multi_ids_mode()
        elif self.filter_ids is not None:
            self._validate_direct_ids_mode()
        else:
            self._validate_csv_mode()

    def _validate_multi_ids_mode(self) -> None:
        """Validate multi-field IDs mode configuration."""
        if not self.multi_filter_ids:
            raise ValueError("multi_filter_ids must be non-empty when set")

    def _validate_direct_ids_mode(self) -> None:
        """Validate direct IDs mode configuration."""
        if not self.filter_field:
            raise ValueError("filter_field is required when filter_ids is set")

    def _validate_csv_mode(self) -> None:
        """Validate CSV-based filter configuration.

        Note: column_name and filter_field can be empty here; they will be
        resolved from YAML configuration during the bootstrap phase.
        """
        if not self.source_path:
            raise ValueError("source_path is required when filter is enabled")


@dataclass(frozen=True, slots=True)
class VacuumConfig:
    """Vacuum operation configuration with tri-state enabled flag.

    The enabled field supports three states:
    - None: Use YAML config default (no CLI override)
    - True: CLI explicitly enables vacuum
    - False: CLI explicitly disables vacuum

    This allows CLI --vacuum.enabled=false to override YAML auto_vacuum=true.
    """

    enabled: bool | None = None
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
    - Composite mode: ignore_yaml_filter bypasses YAML input_filter config
    """

    # Required fields (no defaults)
    pipeline_name: str
    run_id: RunID
    run_type: RunType

    # Defaulted fields (explicit non-None defaults)
    resume: bool = False
    dry_run: bool = False
    vacuum: VacuumConfig = field(default_factory=VacuumConfig)
    input_filter: InputFilterContext = field(
        default_factory=InputFilterContext.disabled
    )
    cached_bronze: CachedBronzeContext = field(
        default_factory=CachedBronzeContext.disabled
    )

    # Truly optional fields (None means "not specified, use config default")
    limit: int | None = None
    query: str | None = None

    # Logging configuration
    log_level: str = "INFO"

    # Composite mode: ignore YAML input_filter config (use only CLI filter)
    ignore_yaml_filter: bool = False

    # Composite mode: skip Gold layer writing (sub-pipelines produce merged Gold separately)
    skip_gold: bool = False

    @property
    def has_input_filter(self) -> bool:
        """Check if input filtering is enabled."""
        return self.input_filter.enabled

    @property
    def has_cached_bronze(self) -> bool:
        """Check if cached Bronze mode is enabled."""
        return self.cached_bronze.enabled

    @property
    def vacuum_enabled(self) -> bool | None:
        """Check if vacuum is enabled (tri-state).

        Returns:
            True: CLI explicitly enabled vacuum
            False: CLI explicitly disabled vacuum
            None: No CLI override, use YAML config default
        """
        return self.vacuum.enabled
