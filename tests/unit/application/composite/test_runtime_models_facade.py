"""Unit tests for the stable composite runtime-model facade."""

from __future__ import annotations

from bioetl.application.composite.runtime_models import (
    CompositeExecutionContext,
    CompositeRuntimeConfig,
)
from bioetl.application.composite.runner_pkg.runner_models import (
    CompositeExecutionContext as CanonicalCompositeExecutionContext,
)
from bioetl.application.composite.runner_pkg.runner_models import (
    CompositeRuntimeConfig as CanonicalCompositeRuntimeConfig,
)


def test_runtime_models_facade_reexports_canonical_runtime_models() -> None:
    """Stable runtime facade should re-export canonical runner models unchanged."""
    assert CompositeRuntimeConfig is CanonicalCompositeRuntimeConfig
    assert CompositeExecutionContext is CanonicalCompositeExecutionContext
