"""Public types for composition layer.

This module provides type definitions and re-exports for external annotation needs.
Use these types when you need to annotate variables or function parameters
that work with composition-layer constructs.

For actual runtime imports, use the specific modules:
- ObservabilityBundle: from bioetl.composition.observability
- StorageBundle: from bioetl.composition.factories.storage.storage_factory
- PipelineRegistry: from bioetl.composition.registry_api
- create_registry: from bioetl.composition.registry_api (isolated instance for tests)
- get_default_registry: shared default-registry export from registry_api

Typed contexts for bootstrap functions (replacing untyped tuples):
- PipelineCallbacksContext: transform, gold_filter, gold_transform callbacks
- DQConfigsContext: Bronze/Silver/Gold DQ report configurations
- DQOutputPathsContext: DQ report output paths and flat_structure flag
- RateLimitContext: rate and capacity for token bucket
- CircuitBreakerConfig: failure_threshold and recovery_timeout
"""

from __future__ import annotations

from bioetl.composition.bootstrap_contexts import (
    CircuitBreakerConfig,
    DQConfigsContext,
    DQOutputPathsContext,
    PipelineCallbacksContext,
    RateLimitContext,
)
from bioetl.composition.factories.storage import StorageBundle
from bioetl.composition.observability import ObservabilityBundle
from bioetl.composition.registry_api import (
    PipelineDefinition,
    PipelineRegistry,
    create_registry,
    get_default_registry,
)

__all__ = [
    "CircuitBreakerConfig",
    "DQConfigsContext",
    "DQOutputPathsContext",
    "ObservabilityBundle",
    "PipelineCallbacksContext",
    "PipelineDefinition",
    "PipelineRegistry",
    "RateLimitContext",
    "StorageBundle",
    "create_registry",
    "get_default_registry",
]
