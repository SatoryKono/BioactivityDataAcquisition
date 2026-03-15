"""Composite pipeline application services.

This package contains application services for composite pipeline orchestration:
- CompositePipelineRunnerService: Main orchestrator for composite pipelines
- DependencyCoordinatorService: Sequential execution of dependency pipelines
- EnrichmentCoordinatorService: Fan-out/fan-in coordination for enrichers
- MergeService: Data merging with conflict resolution
- KeyExtractorService: Extract join keys from seed Silver tables
- CompositeCheckpointService: Checkpoint management for resume capability
- ColumnRenamer: Unified column renaming to qualified format
- ColumnOrderer: Semantic column ordering for consistent output
- CompositePreflightValidationService: Preflight validation for field_priorities

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointManager,
    CompositeCheckpointService,
    CompositeCheckpointState,
)
from bioetl.application.composite.column_orderer import ColumnOrderer
from bioetl.application.composite.column_renamer import ColumnRenamer
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

__all__ = [
    "ColumnOrderer",
    "ColumnRenamer",
    "CompositeCheckpointManager",
    "CompositeCheckpointService",
    "CompositeCheckpointState",
    "CompositePipelineRunner",
    "CompositePipelineRunnerService",
    "CompositePreflightValidationService",
    "CompositePreflightValidator",
    "DependencyCoordinatorService",
    "EnrichmentCoordinatorService",
    "KeyExtractorService",
    "MergeService",
    "PreflightValidationError",
    "PreflightValidationResult",
]
