"""Unit tests for the composite runtime compatibility facades."""

from __future__ import annotations

import pytest

from bioetl.application.composite.runtime_models import (
    CompositeRunnerDependencies,
    CompositeExecutionContext,
    CompositeRuntimeConfig,
)
from bioetl.application.composite.runner_pkg import (
    CompositeRunnerDependencies as RunnerPkgCompositeRunnerDependencies,
    CompositeRuntimeConfig as RunnerPkgCompositeRuntimeConfig,
)


pytestmark = pytest.mark.unit

def test_runner_pkg_facade_reexports_runtime_models() -> None:
    """Legacy runner_pkg facade should preserve canonical runtime model identity."""
    assert CompositeRuntimeConfig is RunnerPkgCompositeRuntimeConfig
    assert CompositeRunnerDependencies is RunnerPkgCompositeRunnerDependencies


def test_runtime_models_exports_execution_context_directly() -> None:
    """Execution context remains available from the stable runtime facade."""
    assert CompositeExecutionContext.__name__ == "CompositeExecutionContext"
