"""Unit tests for base_transformer dependency compatibility re-export."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_transformer_dependency_context_reexport() -> None:
    """Legacy dependencies module re-exports canonical dependency context."""
    from bioetl.application.core.base_transformer.dependencies import (
        TransformerDependencyContext,
    )
    from bioetl.application.core.base_transformer.types import (
        TransformerDependencyContext as CanonicalTransformerDependencyContext,
    )

    assert TransformerDependencyContext is CanonicalTransformerDependencyContext
