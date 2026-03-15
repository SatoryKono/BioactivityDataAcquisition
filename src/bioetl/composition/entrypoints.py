"""Entrypoints for BioETL pipeline operations.

Provides high-level functions for running pipelines and managing resources.
These entrypoints are designed to be used by CLI, REST APIs, or any other
orchestration layer without direct dependency on bootstrap functions.

This module provides the unified pipeline execution interface (REQ-ARCH-041).
Any orchestration layer should use these entrypoints instead of bootstrap.

Split into submodules per audit-package-structure-2026-02-07:
- _pipeline_execution: Core pipeline build/run functions
- _resource_management: Legacy managers, maintenance, inspection
- _services: Application and infrastructure service factories
"""

from __future__ import annotations

# Re-export canonical DTO classes from application.services (H1 refactoring)
# These are the single source of truth for pipeline execution interfaces.
from bioetl.application.services import PipelineRunResult, RunOptions, RunResult
from bioetl.composition._pipeline_execution import (
    ArchiveOptions,
    VacuumOptions,
    build_pipeline_context,
    create_pipeline_runner,
    ensure_metrics_server_started,
    push_metrics_to_gateway,
    run_pipeline,
)
from bioetl.composition._resource_management import (
    archive_table,
    get_checkpoint_manager,
    get_lifecycle_service,
    get_quarantine_manager,
    inspect_quarantine,
    list_checkpoints,
    preview_cleanup,
    vacuum_table,
)
from bioetl.composition._services import (
    cleanup_bronze,
    get_adr_service,
    get_bronze_cleanup_service,
    get_checkpoint_service,
    get_config_service,
    get_export_service,
    get_health_server_dependencies,
    get_health_service,
    get_lock_service,
    get_metrics_service,
    get_pipeline_runner_service,
    get_quarantine_service,
    get_quarantine_store,
    get_vacuum_service,
)
from bioetl.composition.bootstrap import (
    bootstrap_composite_runner,
    load_composite_config,
    load_pipeline_config,
    maybe_start_metrics_server,
)
from bioetl.composition.bootstrap.runtime.observability import start_metrics_server

__all__ = [
    "ArchiveOptions",
    "PipelineRunResult",
    "RunOptions",
    "RunResult",
    "VacuumOptions",
    "archive_table",
    "bootstrap_composite_runner",
    "build_pipeline_context",
    "cleanup_bronze",
    "create_pipeline_runner",
    "ensure_metrics_server_started",
    "get_adr_service",
    "get_bronze_cleanup_service",
    "get_checkpoint_manager",
    "get_checkpoint_service",
    "get_config_service",
    "get_export_service",
    "get_health_server_dependencies",
    "get_health_service",
    "get_lifecycle_service",
    "get_lock_service",
    "get_metrics_service",
    "get_pipeline_runner_service",
    "get_quarantine_manager",
    "get_quarantine_service",
    "get_quarantine_store",
    "get_vacuum_service",
    "inspect_quarantine",
    "list_checkpoints",
    "load_composite_config",
    "load_pipeline_config",
    "maybe_start_metrics_server",
    "preview_cleanup",
    "push_metrics_to_gateway",
    "run_pipeline",
    "start_metrics_server",
    "vacuum_table",
]
