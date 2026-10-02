"""Behavioral coverage for runtime-builder lazy module exports (AUD-009)."""

from __future__ import annotations

import pytest

import bioetl.composition.runtime_builders.inputs_resolver as resolver


pytestmark = pytest.mark.unit


def test_inputs_resolver_compat_symbol_and_unknown() -> None:
    assert (
        resolver.__getattr__("ResolvedVacuumSettings")
        is resolver.ResolvedVacuumSettings
    )
    with pytest.raises(AttributeError, match="has no attribute"):
        resolver.__getattr__("does_not_exist")
