"""Composite pipeline application services.

This package contains application services for composite pipeline orchestration:
- CompositePipelineRunner: Main orchestrator for composite pipelines
- EnrichmentCoordinator: Fan-out/fan-in coordination for enrichers
- MergeService: Data merging with conflict resolution
- KeyExtractorService: Extract join keys from seed Silver tables
- CompositeCheckpointManager: Checkpoint management for resume capability

See ADR-026 for architectural decisions.
"""

from bioetl.application.composite.checkpoint import (
    CompositeCheckpointManager,
    CompositeCheckpointState,
)
from bioetl.application.composite.coordinator import EnrichmentCoordinator
from bioetl.application.composite.key_extractor import KeyExtractorService
from bioetl.application.composite.merger import MergeService
from bioetl.application.composite.runner import CompositePipelineRunner

__all__ = [
    "CompositeCheckpointManager",
    "CompositeCheckpointState",
    "CompositePipelineRunner",
    "EnrichmentCoordinator",
    "KeyExtractorService",
    "MergeService",
]
