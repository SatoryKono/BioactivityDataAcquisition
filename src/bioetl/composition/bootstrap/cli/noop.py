"""Centralized NoOp dependency factory functions for CLI bootstrap.

Contains pure factory functions for creating NoOp implementations used by
CLI-specific bootstrap functions. These provide silent/null implementations
for observability dependencies when full observability is not needed.

Usage:
    # In CLI bootstrap modules
    from bioetl.composition.bootstrap.cli.noop import create_noop_logger

    logger = create_noop_logger()

Design Decisions:
    - Pure functions, not singletons or factory objects
    - Each call creates a new instance (no hidden state sharing)
    - CLI-specific: warn_on_use=False for metrics (intentional opt-out)
    - MUST NOT be imported by runtime code

Note:
    This module centralizes NoOp creation to eliminate duplication across
    CLI bootstrap modules. Runtime observability uses different bootstrap
    functions from composition/bootstrap/runtime/observability.py.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from bioetl.application.services.workflow.control_plane.mutation_plan import (
    WorkflowMutationSpec,
)
from bioetl.composition.factories.dq.composite_validation import (
    resolve_target_table_paths,
)
from bioetl.domain.ports.noop import (
    NoOpMetrics,
    NoOpTracing,
)
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.workflow_config import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowStepConfig,
)
from bioetl.infrastructure.storage.delta.table_ops import resolve_delta_table_path

__all__ = [
    "create_noop_logger",
    "create_noop_metrics",
    "create_noop_observability_bundle",
    "create_noop_tracing",
]


def create_noop_logger() -> NoOpLogger:
    """Create a NoOpLogger instance for CLI operations.

    Returns a logger that silently ignores all logging calls.
    Used by CLI bootstrap functions that don't require full observability.

    Returns:
        NoOpLogger instance implementing LoggerPort interface.

    Example:
        >>> logger = create_noop_logger()
        >>> logger.info("This will be silently ignored")
    """
    return NoOpLogger()


def create_noop_metrics() -> NoOpMetrics:
    """Create a NoOpMetrics instance for CLI operations.

    Returns a metrics collector that silently ignores all metrics.
    Uses warn_on_use=False since CLI intentionally opts out of metrics.

    Returns:
        NoOpMetrics adapter-facing implementation (satisfies MetricsPort).

    Example:
        >>> metrics = create_noop_metrics()
        >>> metrics.increment_counter("test", 1, {"label": "value"})
    """
    return NoOpMetrics(warn_on_use=False)


def create_noop_tracing() -> NoOpTracing:
    """Create a NoOpTracing instance for CLI operations.

    Returns a tracer that does nothing when spans are created.
    Used when distributed tracing is not needed for CLI commands.

    Returns:
        NoOpTracing adapter-facing implementation (satisfies TracingPort).

    Example:
        >>> tracing = create_noop_tracing()
        >>> tracer = tracing.get_tracer("cli")
        >>> with tracer.start_as_current_span("operation"):
        ...     pass  # Span is silently ignored
    """
    return NoOpTracing()


def create_noop_observability_bundle() -> tuple[NoOpLogger, NoOpMetrics, NoOpTracing]:
    """Create a complete NoOp observability bundle for CLI operations.

    Convenience function that creates all three NoOp implementations
    in a single call. Useful when a CLI bootstrap function needs
    multiple observability dependencies.

    Returns:
        Tuple of (NoOpLogger, NoOpMetrics, NoOpTracing) instances.

    Example:
        >>> logger, metrics, tracing = create_noop_observability_bundle()
        >>> # Use in service construction
        >>> service = SomeService(logger=logger, metrics=metrics)
    """
    return (
        create_noop_logger(),
        create_noop_metrics(),
        create_noop_tracing(),
    )


@dataclass(frozen=True, slots=True)
class _PipelineIntent:
    step: WorkflowStepConfig
    paths: tuple[Path, Path]
    dry_run: bool
    destructive: bool
    bounded: bool

    @property
    def bounded_destructive(self) -> bool:
        return self.destructive and self.bounded


def _has_pending_writes(
    writers: tuple[_PipelineIntent, ...], transforms: tuple[TransformStepConfig, ...]
) -> bool:
    return bool(writers) or any(not _verification_only(step) for step in transforms)


def _validate_upstream_profile(
    profile: str, risky: tuple[_PipelineIntent, ...]
) -> None:
    if profile in {"V31", "V32"} and risky:
        raise ValueError(
            "bounded destructive upstream cannot replace the reference cohort of an "
            f"existing {profile} target"
        )


def _verification_only(step: TransformStepConfig) -> bool:
    values = step.config or {}
    return (
        values.get("require_closed_cohort") is True
        and values.get("reconciliation_mode", "complete-reference")
        == "complete-reference"
    )


def _bounded_options(options: dict[str, object]) -> bool:
    return any(
        options.get(name) is not None
        for name in (
            "limit",
            "start_offset",
            "input_csv",
            "filter_ids",
            "multi_filter_ids",
            "cached_bronze_path",
            "cached_bronze_date",
        )
    )


def _bounded_pipeline(config: PipelineYamlConfig, options: dict[str, object]) -> bool:
    yaml_subset = config.input_filter.enabled and not options.get("ignore_yaml_filter")
    return (
        _bounded_options(options)
        or bool(options.get("use_cached_bronze"))
        or yaml_subset
    )


def _resolved_pipeline_paths(
    settings: Settings, config: PipelineYamlConfig
) -> tuple[Path, Path]:
    silver, gold = resolve_target_table_paths(settings, config)
    return silver.resolve(), gold.resolve()


def _transform_path(settings: Settings, layer: str, table: str) -> Path:
    base = settings.gold_path if layer == "gold" else settings.silver_path
    return Path(
        resolve_delta_table_path(
            base_path=str(base), table_name=table, flat_structure=False
        )
    ).resolve()


def _pending_pipeline_writers(
    intents: tuple[_PipelineIntent, ...],
    paths: tuple[Path, Path],
    plan: WorkflowMutationSpec,
) -> tuple[_PipelineIntent, ...]:
    return tuple(
        item
        for item in intents
        if item.step.step_id in plan.pending_step_ids
        and not item.dry_run
        and bool(set(item.paths).intersection(paths))
    )


def _target_transforms(
    config: WorkflowConfig,
    settings: Settings,
    paths: tuple[Path, Path],
    plan: WorkflowMutationSpec,
) -> tuple[TransformStepConfig, ...]:
    if config.defaults.dry_run:
        return ()
    return tuple(
        step
        for step in config.steps
        if isinstance(step, TransformStepConfig)
        and step.step_id in plan.pending_step_ids
        and _transform_writes_paths(step, settings, paths)
    )


def _transform_writes_paths(
    step: TransformStepConfig, settings: Settings, paths: tuple[Path, Path]
) -> bool:
    values = step.config or {}
    source = values.get("source_table")
    if not isinstance(source, str):
        return False
    if step.transform_name in {"summarize_upstream_outputs", "reconcile_rows"}:
        return False
    layer = str(values.get("mutation_layer") or values.get("source_layer", "silver"))
    return _transform_path(settings, layer, source) in paths


def _ancestors(config: WorkflowConfig, step_id: str) -> frozenset[str]:
    definitions = {step.step_id: step for step in config.steps}
    pending = list(definitions[step_id].depends_on)
    found: set[str] = set()
    while pending:
        current = pending.pop()
        if current not in found:
            found.add(current)
            pending.extend(definitions[current].depends_on)
    return frozenset(found)


def _bounded_destructive_upstream(
    config: WorkflowConfig,
    settings: Settings,
    intents: tuple[_PipelineIntent, ...],
    transforms: tuple[TransformStepConfig, ...],
    plan: WorkflowMutationSpec,
    paths: tuple[Path, Path],
) -> tuple[_PipelineIntent, ...]:
    upstream = _reference_producers(config, settings, intents, transforms, paths)
    active = (
        item
        for item in intents
        if item.step.step_id in plan.pending_step_ids and not item.dry_run
    )
    return tuple(
        item
        for item in active
        if item.step.step_id in upstream and item.bounded_destructive
    )


def _reference_producers(
    config: WorkflowConfig,
    settings: Settings,
    intents: tuple[_PipelineIntent, ...],
    transforms: tuple[TransformStepConfig, ...],
    paths: tuple[Path, Path],
) -> set[str]:
    producers = _target_reference_producers(intents, paths)
    for step in transforms:
        producers.update(
            _transform_reference_producers(config, settings, intents, step)
        )
    return producers


def _target_reference_producers(
    intents: tuple[_PipelineIntent, ...], paths: tuple[Path, Path]
) -> set[str]:
    return {
        item.step.reference_cohort.step_id
        for item in intents
        if item.step.pipeline_name == "chembl_target"
        and bool(set(item.paths).intersection(paths))
        and item.step.reference_cohort is not None
    }


def _transform_reference_producers(
    config: WorkflowConfig,
    settings: Settings,
    intents: tuple[_PipelineIntent, ...],
    step: TransformStepConfig,
) -> set[str]:
    values = step.config or {}
    if values.get("reconciliation_mode", "complete-reference") == "selected-snapshot":
        return set()
    reference = _declared_transform_path(settings, values, "reference")
    ancestors = _ancestors(config, step.step_id)
    return {
        item.step.step_id
        for item in intents
        if item.step.step_id in ancestors and reference in item.paths
    }


def _declared_transform_path(
    settings: Settings, values: Mapping[str, object], role: str
) -> Path | None:
    table = values.get(role + "_table")
    if not isinstance(table, str):
        return None
    return _transform_path(settings, str(values.get(role + "_layer", "silver")), table)
