"""Unit tests for composite runtime-model facade."""

from __future__ import annotations

from bioetl.application.composite.runtime_models import (
    CompositeExecutionContext,
    CompositeRuntimeConfig,
)
from bioetl.application.composite.runner_pkg.runner_models import (
    CompositeExecutionContext as CompositeExecutionContextImpl,
)
from bioetl.application.composite.runner_pkg.runner_models import (
    CompositeRuntimeConfig as CompositeRuntimeConfigImpl,
)


def test_runtime_models_facade_reexports_runner_models_symbols() -> None:
    """Facade should preserve identity of runtime model symbols."""
    assert CompositeRuntimeConfig is CompositeRuntimeConfigImpl
    assert CompositeExecutionContext is CompositeExecutionContextImpl
