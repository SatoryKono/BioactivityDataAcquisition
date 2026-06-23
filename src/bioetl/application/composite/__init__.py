"""Composite pipeline application services.

This package contains application services for composite pipeline orchestration:
- CompositePipelineRunner: Main orchestrator for composite pipelines
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
    PreflightValidationError,
    PreflightValidationResult,
)
from bioetl.application.composite.runner_pkg import CompositePipelineRunner
from bioetl.application.composite.runtime_models import CompositeRuntimeConfig
from bioetl.domain.composite.state import CompositePipelineState

__all__ = [
    "ColumnOrderService",
    "ColumnRenamer",
    "CompositeCheckpointService",
    "CompositeCheckpointState",
    "CompositePipelineRunner",
    "CompositePipelineState",
    "CompositePreflightValidationService",
    "CompositeRuntimeConfig",
    "DependencyCoordinatorService",
    "EnrichmentCoordinatorService",
    "KeyExtractorService",
    "MergeService",
    "PreflightValidationError",
    "PreflightValidationResult",
]
