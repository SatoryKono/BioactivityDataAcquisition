"""Ratchet for composition modules that still rely on smoke-only confidence.

This file intentionally stays tiny. When a composition module gains dedicated
unit coverage, it should be removed from the lists below so the remaining
smoke-only surface trends toward zero.
"""

from __future__ import annotations

import pytest

# bootstrap/runtime modules still relying on smoke/import confidence
_BOOTSTRAP_RUNTIME_MODULES: list[str] = []

# factories/pipeline modules still relying on smoke/import confidence
_FACTORY_PIPELINE_MODULES: list[str] = []

# factories/services modules still relying on smoke/import confidence
_FACTORY_SERVICES_MODULES: list[str] = []

# factories/storage modules still relying on smoke/import confidence
_FACTORY_STORAGE_MODULES: list[str] = []

_ALL_COMPOSITION_MODULES = (
    _BOOTSTRAP_RUNTIME_MODULES
    + _FACTORY_PIPELINE_MODULES
    + _FACTORY_SERVICES_MODULES
    + _FACTORY_STORAGE_MODULES
)


@pytest.mark.smoke
class TestCompositionSmokeOnlyRatchet:
    """Ensure composition no longer depends on smoke-only module imports."""

    def test_no_composition_modules_rely_on_smoke_only_confidence(self) -> None:
        """All critical composition seams should have dedicated unit coverage."""
        assert _ALL_COMPOSITION_MODULES == []
