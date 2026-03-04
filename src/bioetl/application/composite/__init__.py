"""Composite pipeline application services.

This package contains application services for composite pipeline orchestration:
- CompositePipelineRunnerService: Main orchestrator for composite pipelines
- DependencyCoordinatorService: Sequential execution of dependency pipelines
- EnrichmentCoordinatorService: Fan-out/fan-in coordination for enrichers
- MergeService: Data merging with conflict resolution
- KeyExtractorService: Extract join keys from seed Silver tables
- CompositeCheckpointService: Checkpoint management for resume capability
- ColumnRenamerService: Unified column renaming to qualified format
- ColumnOrdererService: Semantic column ordering for consistent output
- CompositePreflightValidationService: Preflight validation for field_priorities

See ADR-026 for architectural decisions.
"""

from __future__ import annotations

import warnings

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointManager,
    CompositeCheckpointService,
    CompositeCheckpointState,
)
from bioetl.application.composite.column_orderer import ColumnOrdererService
from bioetl.application.composite.column_renamer import ColumnRenamerService
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
from bioetl.application.composite.runner import (
    CompositePipelineRunner,
    CompositePipelineRunnerService,
)

_DEPRECATED_CLASS_ALIASES: dict[str, type[object]] = {
    "ColumnOrderer": ColumnOrdererService,
    "ColumnRenamer": ColumnRenamerService,
    "DependencyCoordinator": DependencyCoordinatorService,
    "EnrichmentCoordinator": EnrichmentCoordinatorService,
}


def __getattr__(name: str) -> object:
    """Resolve deprecated class aliases lazily."""
    replacement = _DEPRECATED_CLASS_ALIASES.get(name)
    if replacement is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    warnings.warn(
        f"{name} is deprecated; use {replacement.__name__}.",
        DeprecationWarning,
        stacklevel=2,
    )
    return replacement


__all__ = [
    "ColumnOrderer",
    "ColumnOrdererService",
    "ColumnRenamer",
    "ColumnRenamerService",
    "CompositeCheckpointManager",
    "CompositeCheckpointService",
    "CompositeCheckpointState",
    "CompositePipelineRunner",
    "CompositePipelineRunnerService",
    "CompositePreflightValidationService",
    "CompositePreflightValidator",
    "DependencyCoordinator",
    "DependencyCoordinatorService",
    "EnrichmentCoordinator",
    "EnrichmentCoordinatorService",
    "KeyExtractorService",
    "MergeService",
    "PreflightValidationError",
    "PreflightValidationResult",
]
