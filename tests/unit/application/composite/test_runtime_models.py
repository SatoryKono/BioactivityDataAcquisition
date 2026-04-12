"""Unit tests for canonical composite runtime models."""

from __future__ import annotations

from bioetl.application.composite.runtime_models import (
    CompositeRunnerDependencies,
    CompositeRunnerDependencyGroup,
    CompositeExecutionContext,
    CompositeRuntimeConfig,
)


def test_runtime_models_exports_stable_symbols() -> None:
    """Stable runtime module should own the canonical orchestration models."""
    assert CompositeRuntimeConfig.__name__ == "CompositeRuntimeConfig"
    assert CompositeExecutionContext.__name__ == "CompositeExecutionContext"


def test_runtime_models_preserves_legacy_dependency_alias() -> None:
    """Legacy dependency alias should still resolve to the canonical dataclass."""
    assert CompositeRunnerDependencies is CompositeRunnerDependencyGroup
