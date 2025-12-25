"""Bootstrap submodule for BioETL Composition Root.

Provides modular bootstrap functions organized by responsibility:
- observability: logging, tracing, metrics, data quality monitoring
- storage: storage adapters, cleanup, lifecycle services
- checkpoint: checkpoint and quarantine management

All functions are re-exported for backward compatibility with
the main bootstrap module.
"""

from __future__ import annotations

from bioetl.composition._bootstrap.checkpoint import (
    bootstrap_checkpoint,
    bootstrap_checkpoint_manager,
    bootstrap_quarantine,
    bootstrap_quarantine_manager,
)
from bioetl.composition._bootstrap.observability import (
    bootstrap_dq_monitor,
    bootstrap_logger,
    bootstrap_metrics,
    bootstrap_observability,
    bootstrap_tracer,
)
from bioetl.composition._bootstrap.storage import (
    bootstrap_cleanup,
    bootstrap_lifecycle_service,
    bootstrap_storage,
)

__all__ = [
    "bootstrap_checkpoint",
    "bootstrap_checkpoint_manager",
    "bootstrap_cleanup",
    "bootstrap_dq_monitor",
    "bootstrap_lifecycle_service",
    "bootstrap_logger",
    "bootstrap_metrics",
    "bootstrap_observability",
    "bootstrap_quarantine",
    "bootstrap_quarantine_manager",
    "bootstrap_storage",
    "bootstrap_tracer",
]
