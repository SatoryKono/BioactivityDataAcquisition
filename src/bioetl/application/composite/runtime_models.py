"""Stable runtime data models for composite pipeline orchestration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from bioetl.application.runtime_clock import RuntimeClock
from bioetl.domain.composite.result import (
    DependencyResult,
    EnrichmentResult,
    MergeResult,
    SeedResult,
)
from bioetl.domain.constants import DEFAULT_LOCK_TTL_SECONDS

if TYPE_CHECKING:
    import polars as pl

    from bioetl.application.composite.checkpoint import (
        CompositeCheckpointService,
    )
    from bioetl.application.composite.coordinator import (
        EnrichmentCoordinatorService,
    )
    from bioetl.application.composite.dependency_coordinator import (
        DependencyCoordinatorService,
    )
    from bioetl.application.composite.fsm_helper import (
        FSMStateHelperService,
    )
    from bioetl.application.composite.key_extractor import (
        KeyExtractorService,
    )
    from bioetl.application.composite.lifecycle_observer_service import (
        CompositeLifecycleObserverService,
    )
    from bioetl.application.composite.merger import (
        MergeService,
    )
    from bioetl.application.composite.preflight_validator import (
        CompositePreflightValidationService,
    )
    from bioetl.application.services.control_plane.run_ledger_service import (
        RunLedgerService,
    )
    from bioetl.application.services.dq_report_service import DQReportService
    from bioetl.domain.ports import (
        ClockPort,
        ExecutionMetricsRunnerPort,
        LockPort,
        LoggerPort,
        MetricsPort,
        QuarantinePort,
        TracingPort,
    )

__all__ = [
    "CompositeExecutionContext",
    "CompositeRunnerDependencies",
    "CompositeRunnerDependencyGroup",
    "CompositeRuntimeConfig",
]


@dataclass(frozen=True, slots=True)
class CompositeRuntimeConfig:
    """Runtime configuration for composite pipeline execution."""

    resume: bool = False
    dry_run: bool = False
    enrich_only: tuple[str, ...] | None = None
    required_only: bool = False
    force_enricher: str | None = None
    seed_limit: int | None = None
    use_cached_bronze: bool = False
    cached_bronze_path: str | None = None
    cached_bronze_date: str | None = None
    cached_bronze_enrichers: bool | None = None
    cached_bronze_dependencies: bool = False
    heartbeat_interval_seconds: int = 30
    lock_ttl_seconds: int = DEFAULT_LOCK_TTL_SECONDS

    def __post_init__(self) -> None:
        """Normalize mutable values into immutable runtime fields."""
        if isinstance(self.enrich_only, list):
            object.__setattr__(self, "enrich_only", tuple(self.enrich_only))


@dataclass(frozen=True, slots=True)
class CompositeRunnerDependencyGroup:
    """Grouped dependencies for ``CompositePipelineRunner`` construction."""

    seed_runner_factory: Callable[[], ExecutionMetricsRunnerPort]
    enricher_runner_factory: Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort]
    key_extractor: KeyExtractorService
    coordinator: EnrichmentCoordinatorService
    merger: MergeService
    checkpoint_manager: CompositeCheckpointService
    logger: LoggerPort
    lock: LockPort
    fsm_state_helper: FSMStateHelperService | None
    dq_report_service: DQReportService | None = None
    preflight_validator: CompositePreflightValidationService | None = None
    dependencies_runner_factory: (
        Callable[[str, pl.DataFrame], ExecutionMetricsRunnerPort] | None
    ) = None
    dependency_coordinator: DependencyCoordinatorService | None = None
    quarantine_port: QuarantinePort | None = None
    metrics: MetricsPort | None = None
    tracer: TracingPort | None = None
    observer: CompositeLifecycleObserverService | None = None
    manifest_id: str | None = None
    run_ledger_service: RunLedgerService | None = None
    clock: ClockPort = field(default_factory=RuntimeClock)


CompositeRunnerDependencies = CompositeRunnerDependencyGroup


@dataclass(frozen=True, slots=True)
class CompositeExecutionContext:
    """Named stage outputs passed into final result assembly."""

    seed_result: SeedResult
    dependency_results: dict[str, DependencyResult]
    enrichment_results: dict[str, EnrichmentResult]
    merge_result: MergeResult | None
