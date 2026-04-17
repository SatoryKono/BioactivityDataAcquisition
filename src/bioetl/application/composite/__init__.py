"""Composite pipeline application services.

This package contains application services for composite pipeline orchestration:
- CompositePipelineRunnerService: Main orchestrator for composite pipelines
- DependencyCoordinatorService: Sequential execution of dependency pipelines
- EnrichmentCoordinatorService: Fan-out/fan-in coordination for enrichers
- MergeService: Data merging with conflict resolution
- KeyExtractorService: Extract join keys from seed Silver tables
- CompositeCheckpointService: Checkpoint management for resume capability
- ColumnRenamer: Unified column renaming to qualified format
- ColumnOrderService: Unified column ordering service (semantic + priority)
- CompositePreflightValidationService: Preflight validation for field_priorities

See ADR-026 for architectural decisions.

Internal composition-facing seams:
- ``bioetl.application.composite.runtime_wiring_api`` — bootstrap/runtime wiring
"""

from __future__ import annotations

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointManager,
    CompositeCheckpointService,
    CompositeCheckpointState,
)
from bioetl.application.composite.column_renamer import ColumnRenamer
from bioetl.application.composite.column_service import ColumnOrderService
from bioetl.application.composite.coordinator import EnrichmentCoordinatorService
from bioetl.application.composite.dependency_coordinator import (
    DependencyCoordinatorService,
)
from bioetl.application.composite.key_extractor import KeyExtractorService
from bioetl.application.composite.merger import MergeService
from bioetl.application.composite.preflight_validator import (
    CompositePreflightValidationService,
    CompositePreflightValidator,
    PreflightValidationError,
    PreflightValidationResult,
)
from bioetl.application.composite.runner_pkg import (
    CompositePipelineRunner,
    CompositePipelineRunnerService,
)
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.domain.composite.state import CompositePipelineState

__all__ = [
    "ColumnOrderService",
    "ColumnRenamer",
    "CompositeCheckpointManager",
    "CompositeCheckpointService",
    "CompositeCheckpointState",
    "CompositePipelineRunner",
    "CompositePipelineRunnerService",
    "CompositePipelineState",
    "CompositePreflightValidationService",
    "CompositePreflightValidator",
    "CompositeRuntimeConfig",
    "DependencyCoordinatorService",
    "EnrichmentCoordinatorService",
    "KeyExtractorService",
    "MergeService",
    "PreflightValidationError",
    "PreflightValidationResult",
]
