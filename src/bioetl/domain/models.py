"""Data models for ETL pipeline core."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from bioetl.domain.providers import ProviderId
from bioetl.domain.value_objects import EntityName, RunId, StageName


@dataclass
class StageResult:
    """Stage execution result.

    Attributes:
        stage_name: Stage name (StageName). Accepts str for backward compatibility.
        success: Execution success status.
        records_processed: Number of processed records.
        chunks_processed: Number of processed chunks.
        duration_sec: Execution duration in seconds.
        errors: List of errors.
    """

    stage_name: StageName
    success: bool
    records_processed: int
    chunks_processed: int
    duration_sec: float
    errors: list[str]

    def __post_init__(self) -> None:
        """Coerce str to StageName for backwards compatibility."""
        if isinstance(self.stage_name, str):
            object.__setattr__(self, "stage_name", StageName(self.stage_name))


@dataclass
class RunContext:
    """Pipeline execution context.

    Contains information about current run, configuration and environment.

    Attributes:
        run_id: Unique run identifier (RunId).
        entity_name: Entity name (EntityName). Accepts str for backward compatibility.
        provider: Provider identifier (ProviderId). Accepts str for backward compatibility.
        started_at: Execution start time.
        config: Run configuration.
        dry_run: Test run flag.
        metadata: Additional metadata.
    """

    run_id: RunId = field(default_factory=RunId.generate)
    entity_name: EntityName | None = None
    provider: ProviderId | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    config: dict[str, Any] = field(default_factory=dict)
    dry_run: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Coerce str to Value Objects for backwards compatibility."""
        if isinstance(self.entity_name, str):
            value = self.entity_name
            if value:
                object.__setattr__(self, "entity_name", EntityName(value))
            else:
                object.__setattr__(self, "entity_name", None)
        if isinstance(self.provider, str):
            value = self.provider
            if value:
                object.__setattr__(self, "provider", ProviderId(value))
            else:
                object.__setattr__(self, "provider", None)


@dataclass
class RunResult:
    """Pipeline execution result."""

    run_id: RunId
    success: bool
    entity_name: str
    row_count: int
    output_path: Path | None
    duration_sec: float
    stages: list[StageResult]
    errors: list[str]
    meta: dict[str, Any]


@dataclass
class StageDescriptor:
    """Pipeline stage descriptor.

    Describes stage, its executable code and metadata.
    """

    name: str
    callable: Callable[..., Any]
    skip_on_dry_run: bool = False
    required: bool = True
