"""Bootstrap submodule for BioETL Composition Root.

Provides modular bootstrap functions organized by responsibility:
- observability: logging, tracing, metrics, data quality monitoring
- storage: storage adapters, cleanup, lifecycle services
- checkpoint: checkpoint and quarantine management
- config: configuration service
- health: health service

All functions are re-exported for backward compatibility with
the main bootstrap module.
"""

from __future__ import annotations

from bioetl.composition._bootstrap.checkpoint import (
    bootstrap_checkpoint,
    bootstrap_checkpoint_manager,
    bootstrap_checkpoint_service,
    bootstrap_quarantine,
    bootstrap_quarantine_manager,
    bootstrap_quarantine_service,
)
from bioetl.composition._bootstrap.config import bootstrap_config_service
from bioetl.composition._bootstrap.health import bootstrap_health_service
from bioetl.composition._bootstrap.lock import bootstrap_lock_service
from bioetl.composition._bootstrap.observability import (
    bootstrap_dq_monitor,
    bootstrap_logger,
    bootstrap_metrics,
    bootstrap_observability,
    bootstrap_tracer,
    validate_observability_preflight,
)
from bioetl.composition._bootstrap.runner import bootstrap_pipeline_runner_service
from bioetl.composition._bootstrap.storage import (
    bootstrap_bronze_cleanup_service,
    bootstrap_cleanup,
    bootstrap_lifecycle_service,
    bootstrap_storage,
    bootstrap_vacuum_service,
)

__all__ = [
    "bootstrap_bronze_cleanup_service",
    "bootstrap_checkpoint",
    "bootstrap_checkpoint_manager",
    "bootstrap_checkpoint_service",
    "bootstrap_cleanup",
    "bootstrap_config_service",
    "bootstrap_dq_monitor",
    "bootstrap_health_service",
    "bootstrap_lifecycle_service",
    "bootstrap_lock_service",
    "bootstrap_logger",
    "bootstrap_metrics",
    "bootstrap_observability",
    "bootstrap_pipeline_runner_service",
    "bootstrap_quarantine",
    "bootstrap_quarantine_manager",
    "bootstrap_quarantine_service",
    "bootstrap_storage",
    "bootstrap_tracer",
    "bootstrap_vacuum_service",
    "validate_observability_preflight",
]
