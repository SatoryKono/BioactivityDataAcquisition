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

from importlib import import_module

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

_LAZY_ATTR_EXPORTS: dict[str, tuple[str, str]] = {
    "ColumnOrderService": (
        "bioetl.application.composite.column_service",
        "ColumnOrderService",
    ),
    "ColumnRenamer": ("bioetl.application.composite.column_renamer", "ColumnRenamer"),
    "CompositeCheckpointManager": (
        "bioetl.application.composite.checkpoint",
        "CompositeCheckpointManager",
    ),
    "CompositeCheckpointService": (
        "bioetl.application.composite.checkpoint",
        "CompositeCheckpointService",
    ),
    "CompositeCheckpointState": (
        "bioetl.application.composite.checkpoint",
        "CompositeCheckpointState",
    ),
    "CompositePipelineRunner": (
        "bioetl.application.composite.runner_pkg",
        "CompositePipelineRunner",
    ),
    "CompositePipelineRunnerService": (
        "bioetl.application.composite.runner_pkg",
        "CompositePipelineRunnerService",
    ),
    "CompositePipelineState": (
        "bioetl.domain.composite.state",
        "CompositePipelineState",
    ),
    "CompositePreflightValidationService": (
        "bioetl.application.composite.preflight_validator",
        "CompositePreflightValidationService",
    ),
    "CompositePreflightValidator": (
        "bioetl.application.composite.preflight_validator",
        "CompositePreflightValidator",
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
        "bioetl.application.composite.preflight_validator",
        "PreflightValidationError",
    ),
    "PreflightValidationResult": (
        "bioetl.application.composite.preflight_validator",
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
