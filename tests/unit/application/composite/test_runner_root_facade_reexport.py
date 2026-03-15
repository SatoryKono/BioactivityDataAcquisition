"""Unit tests for application.composite.runner compatibility re-exports."""

from __future__ import annotations

import pytest


@pytest.mark.unit
def test_runner_root_facade_reexports_canonical_symbols() -> None:
    """Legacy runner root facade should re-export canonical runner package symbols."""
    from bioetl.application.composite.runner import (
        CompositePipelineRunner,
        CompositePipelineRunnerService,
        CompositePipelineState,
        CompositeRuntimeConfig,
    )
    from bioetl.application.composite.runner_pkg.runner import (
        CompositePipelineRunner as CanonicalCompositePipelineRunner,
    )
    from bioetl.application.composite.runner_pkg.runner import (
        CompositePipelineRunnerService as CanonicalCompositePipelineRunnerService,
    )
    from bioetl.application.composite.runner_pkg.runner import (
        CompositeRuntimeConfig as CanonicalCompositeRuntimeConfig,
    )
    from bioetl.domain.composite.state import (
        CompositePipelineState as CanonicalCompositePipelineState,
    )

    assert CompositePipelineRunner is CanonicalCompositePipelineRunner
    assert CompositePipelineRunnerService is CanonicalCompositePipelineRunnerService
    assert CompositeRuntimeConfig is CanonicalCompositeRuntimeConfig
    assert CompositePipelineState is CanonicalCompositePipelineState
