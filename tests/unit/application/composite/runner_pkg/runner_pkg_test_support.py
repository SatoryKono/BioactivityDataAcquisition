"""Shared test support for runner_pkg unit suites."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

from bioetl.application.composite.lifecycle_observer_service import (
    CompositeLifecycleObserverService,
)
from bioetl.domain.composite.result import (
    DependencyResult,
    DependencyStatus,
    EnrichmentResult,
    EnrichmentStatus,
)
from bioetl.domain.composite.state import CompositePipelineState


def make_enricher_cfg(pipeline: str, *, required: bool = False) -> SimpleNamespace:
    """Create a minimal enricher config stub."""
    return SimpleNamespace(pipeline=pipeline, required=required)


def make_dependency_cfg(
    pipeline: str,
    *,
    required: bool = False,
    silver_table: str = "silver/t",
) -> SimpleNamespace:
    """Create a minimal dependency config stub."""
    return SimpleNamespace(
        pipeline=pipeline,
        required=required,
        silver_table=silver_table,
    )


def make_composite_config(
    *,
    name: str = "test_composite",
    enrichers: list[Any] | None = None,
    required_enrichers: list[str] | None = None,
    required_dependencies: list[str] | None = None,
    dependencies: list[Any] | None = None,
) -> SimpleNamespace:
    """Create a configurable composite config stub."""
    return SimpleNamespace(
        name=name,
        enrichers=enrichers or [],
        required_enrichers=required_enrichers or [],
        required_dependencies=required_dependencies or [],
        dependencies=dependencies or [],
        seed=SimpleNamespace(pipeline="seed_pipeline", silver_table="silver/seed"),
        merge=SimpleNamespace(field_priorities=[]),
    )


def make_runner_state(
    *,
    state: CompositePipelineState = CompositePipelineState.NOT_STARTED,
    seed_completed: bool = False,
    completed_dependencies: frozenset[str] | None = None,
    completed_enrichers: frozenset[str] | None = None,
    enrichment_results: dict[str, Any] | None = None,
) -> MagicMock:
    """Create a checkpoint-state mock with common fluent update methods."""
    mock_state = MagicMock()
    mock_state.state = state
    mock_state.seed_completed = seed_completed
    mock_state.completed_dependencies = completed_dependencies or frozenset()
    mock_state.completed_enrichers = completed_enrichers or frozenset()
    mock_state.enrichment_results = enrichment_results or {}
    mock_state.with_state = MagicMock(return_value=mock_state)
    mock_state.with_seed_completed = MagicMock(return_value=mock_state)
    mock_state.with_dependency_completed = MagicMock(return_value=mock_state)
    mock_state.with_enricher_completed = MagicMock(return_value=mock_state)
    return mock_state


def success_dep(name: str) -> DependencyResult:
    """Create a successful dependency result."""
    return DependencyResult(pipeline_name=name, status=DependencyStatus.SUCCESS)


def failed_dep(name: str) -> DependencyResult:
    """Create a failed dependency result."""
    return DependencyResult(pipeline_name=name, status=DependencyStatus.FAILED)


def success_enrichment(name: str) -> EnrichmentResult:
    """Create a successful enrichment result."""
    return EnrichmentResult(enricher_name=name, status=EnrichmentStatus.SUCCESS)


def failed_enrichment(name: str) -> EnrichmentResult:
    """Create a failed enrichment result."""
    return EnrichmentResult(
        enricher_name=name,
        status=EnrichmentStatus.FAILED,
        error_message="test failure",
    )


def make_dependency_lookup(
    dep_cfg: SimpleNamespace,
) -> callable:
    """Create a simple dependency lookup closure for config stubs."""

    def _lookup(name: str) -> SimpleNamespace | None:
        if name == dep_cfg.pipeline:
            return dep_cfg
        return None

    return _lookup


def initialize_runner_pkg_harness(
    harness: object,
    *,
    config: Any,
    runtime: object,
    run_id_str: str,
    with_metrics_and_tracing: bool = False,
) -> None:
    """Attach common runner_pkg harness collaborators to a test double."""
    setattr(harness, "_config", config)
    setattr(harness, "_runtime", runtime)

    logger = MagicMock()
    setattr(harness, "_logger", logger)

    observer_logger = MagicMock()
    setattr(harness, "_observer_logger", observer_logger)
    setattr(
        harness,
        "_observer",
        CompositeLifecycleObserverService(logger=observer_logger),
    )
    setattr(harness, "_run_id_str", run_id_str)
    setattr(harness, "_checkpoint_manager", AsyncMock())
    setattr(harness, "_fsm", MagicMock())

    if with_metrics_and_tracing:
        metrics = MagicMock()
        metrics.increment_counter = MagicMock()
        metrics.observe_histogram = MagicMock()
        tracing = MagicMock()
        tracing.flush = MagicMock()
        otel_tracer = MagicMock()
        checkpoint_span = MagicMock()
        otel_tracer.start_as_current_span.return_value = checkpoint_span
        tracing.get_tracer.return_value = otel_tracer
        setattr(harness, "_metrics", metrics)
        setattr(harness, "_tracing", tracing)
        setattr(harness, "_otel_tracer", otel_tracer)
        setattr(harness, "_checkpoint_span", checkpoint_span)
