"""Unit tests for composite bootstrap builder aliases."""

from __future__ import annotations

import pytest

from bioetl.composition.bootstrap.runtime import composite_bootstrap_builders
from bioetl.composition.bootstrap.runtime import runtime_basics


@pytest.mark.unit
def test_passthrough_builder_exports_alias_runtime_basics() -> None:
    """Pure passthrough builder seams should stay direct aliases."""
    assert (
        composite_bootstrap_builders.build_runner_factories
        is runtime_basics.build_runner_factories
    )
    assert (
        composite_bootstrap_builders.build_support_services
        is runtime_basics.build_support_services
    )
