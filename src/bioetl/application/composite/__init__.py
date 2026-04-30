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

from importlib import import_module

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

_COMPOSITE_CHECKPOINT_MODULE = "bioetl.application.composite.checkpoint"
_COMPOSITE_PREFLIGHT_VALIDATOR_MODULE = (
    "bioetl.application.composite.preflight_validator"
)

_LAZY_ATTR_EXPORTS: dict[str, tuple[str, str]] = {
    "ColumnOrderService": (
        "bioetl.application.composite.column_service",
        "ColumnOrderService",
    ),
    "ColumnRenamer": ("bioetl.application.composite.column_renamer", "ColumnRenamer"),
    "CompositeCheckpointService": (
        _COMPOSITE_CHECKPOINT_MODULE,
        "CompositeCheckpointService",
    ),
    "CompositeCheckpointState": (
        _COMPOSITE_CHECKPOINT_MODULE,
        "CompositeCheckpointState",
    ),
    "CompositePipelineRunner": (
        "bioetl.application.composite.runner_pkg",
        "CompositePipelineRunner",
    ),
    "CompositePipelineState": (
        "bioetl.domain.composite.state",
        "CompositePipelineState",
    ),
    "CompositePreflightValidationService": (
        _COMPOSITE_PREFLIGHT_VALIDATOR_MODULE,
        "CompositePreflightValidationService",
    ),
    "CompositeRuntimeConfig": (
        "bioetl.application.composite.runtime_models",
        "CompositeRuntimeConfig",
    ),
    "DependencyCoordinatorService": (
        "bioetl.application.composite.dependency_coordinator",
        "DependencyCoordinatorService",
    ),
    "EnrichmentCoordinatorService": (
        "bioetl.application.composite.coordinator",
        "EnrichmentCoordinatorService",
    ),
    "KeyExtractorService": (
        "bioetl.application.composite.key_extractor",
        "KeyExtractorService",
    ),
    "MergeService": ("bioetl.application.composite.merger", "MergeService"),
    "PreflightValidationError": (
        _COMPOSITE_PREFLIGHT_VALIDATOR_MODULE,
        "PreflightValidationError",
    ),
    "PreflightValidationResult": (
        _COMPOSITE_PREFLIGHT_VALIDATOR_MODULE,
        "PreflightValidationResult",
    ),
}


def __getattr__(name: str) -> object:
    """Lazily expose composite application services for package imports."""
    try:
        module_name, attr_name = _LAZY_ATTR_EXPORTS[name]
    except KeyError as exc:  # pragma: no cover - standard attribute path
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return stable exports for shell introspection and help()."""
    return sorted(set(globals()) | set(__all__))
