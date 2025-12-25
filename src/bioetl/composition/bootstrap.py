"""Composition Root for BioETL.

Handles the initialization and wiring of infrastructure components (adapters)
to provide a ready-to-use PipelineRunner for execution.

Bootstrap functions are organized into submodules:
- bootstrap.observability: logging, tracing, metrics, DQ monitor
- bootstrap.storage: storage adapters, cleanup, lifecycle services
- bootstrap.checkpoint: checkpoint and quarantine management

All functions are re-exported here for backward compatibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.composition._bootstrap import (
    bootstrap_checkpoint,
    bootstrap_checkpoint_manager,
    bootstrap_cleanup,
    bootstrap_dq_monitor,
    bootstrap_lifecycle_service,
    bootstrap_logger,
    bootstrap_metrics,
    bootstrap_observability,
    bootstrap_quarantine,
    bootstrap_quarantine_manager,
    bootstrap_storage,
    bootstrap_tracer,
)
from bioetl.composition.builders import FilterConfigBuilder
from bioetl.composition.factories.pipeline_factories import register_all_pipelines
from bioetl.composition.factories.storage_factory import StorageAdapter
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.providers.registration import register_all_providers
from bioetl.composition.registry import PipelineRegistry
from bioetl.domain.config import RuntimeConfig
from bioetl.infrastructure.adapters.chembl.client import ChemblAdapter
from bioetl.infrastructure.adapters.http.client import UnifiedHTTPClient
from bioetl.infrastructure.checkpoint.local_checkpoint import LocalCheckpoint
from bioetl.infrastructure.config import get_settings, load_pipeline_config
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.observability.prometheus_metrics import PrometheusMetrics
from bioetl.infrastructure.observability.server import MetricsServerError
from bioetl.infrastructure.quarantine.unified_quarantine import UnifiedQuarantine
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter

__all__ = [
    # Infrastructure components (re-exports for convenience)
    "BronzeWriter",
    "ChemblAdapter",
    "DeltaWriter",
    "GoldWriter",
    "LocalCheckpoint",
    "MemoryLock",
    "MetricsServerError",
    "ObservabilityBundle",
    "PrometheusMetrics",
    "StorageAdapter",
    "UnifiedHTTPClient",
    "UnifiedQuarantine",
    # Bootstrap functions (from submodules)
    "bootstrap_checkpoint",
    "bootstrap_checkpoint_manager",
    "bootstrap_cleanup",
    "bootstrap_dq_monitor",
    "bootstrap_lifecycle_service",
    "bootstrap_logger",
    "bootstrap_metrics",
    "bootstrap_observability",
    "bootstrap_pipeline",
    "bootstrap_quarantine",
    "bootstrap_quarantine_manager",
    "bootstrap_storage",
    "bootstrap_tracer",
    # Config loader
    "load_pipeline_config",
]

if TYPE_CHECKING:
    from bioetl.application.core.runner import PipelineRunner
    from bioetl.domain.context import PipelineRunContext


def bootstrap_pipeline(ctx: PipelineRunContext) -> PipelineRunner:
    """Composition Root: Assembles and returns a fully configured PipelineRunner.

    This is the main entry point for creating a pipeline runner. It:
    1. Registers all providers and pipelines (idempotent)
    2. Loads settings and YAML configuration
    3. Bootstraps observability (logging, tracing, metrics)
    4. Builds filter configuration from CLI/YAML
    5. Delegates to the appropriate factory to create the runner

    Args:
        ctx: Pipeline run context containing launch parameters including
            pipeline_name, run_id, run_type, resume flag, limit, filters, etc.

    Returns:
        PipelineRunner: Fully configured runner ready for execution.

    Example:
        >>> from bioetl.domain.context import PipelineRunContext
        >>> from bioetl.domain.types import RunType
        >>> from uuid import uuid4
        >>>
        >>> ctx = PipelineRunContext(
        ...     pipeline_name="chembl_activity",
        ...     run_id=uuid4(),
        ...     run_type=RunType.INCREMENTAL,
        ... )
        >>> runner = bootstrap_pipeline(ctx)
        >>> await runner.run()
    """
    # Explicit registration (idempotent)
    register_all_providers()
    register_all_pipelines()

    settings = get_settings()

    # Bootstrap unified observability (includes metrics server start if enabled)
    observability = bootstrap_observability(
        pipeline=ctx.pipeline_name,
        run_id=ctx.run_id,
        settings=settings,
    )

    # Load validated YAML config
    yaml_config = load_pipeline_config(ctx.pipeline_name)

    runtime_config = RuntimeConfig(
        run_type=ctx.run_type,
        resume=ctx.resume,
        limit=ctx.limit,
        heartbeat_interval=settings.pipeline.heartbeat_interval,
        query=ctx.query,
        dry_run=ctx.dry_run,
    )

    # Build filter config using the dedicated builder
    filter_config = FilterConfigBuilder.build(
        yaml_filter=yaml_config.input_filter,
        cli_csv=ctx.input_csv,
        cli_column=ctx.filter_column,
        cli_field=ctx.filter_field,
    )

    if filter_config:
        observability.logger.info(
            "input_filter_enabled",
            csv_path=filter_config.source_path,
            column=filter_config.column_name,
            filter_field=filter_config.filter_field,
            source="cli" if ctx.input_csv else "config",
        )

    # Resolve pipeline factory and delegate runner creation
    pipeline_def = PipelineRegistry.get(ctx.pipeline_name)
    factory = pipeline_def.factory

    return factory.create_runner(
        run_id=ctx.run_id,
        runtime=runtime_config,
        settings=settings,
        observability=observability,
        filter_config=filter_config,
        config=yaml_config,
    )
