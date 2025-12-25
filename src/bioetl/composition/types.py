"""Public types for composition layer.

This module provides type definitions and re-exports for external annotation needs.
Use these types when you need to annotate variables or function parameters
that work with composition-layer constructs.

For actual runtime imports, use the specific modules:
- ObservabilityBundle: from bioetl.composition.observability
- StorageAdapter: from bioetl.composition.factories.storage_factory
- PipelineRegistry: from bioetl.composition.registry
"""

from __future__ import annotations

from bioetl.composition.factories.storage_factory import StorageAdapter
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.registry import PipelineDefinition, PipelineRegistry

__all__ = [
    "ObservabilityBundle",
    "PipelineDefinition",
    "PipelineRegistry",
    "StorageAdapter",
]
