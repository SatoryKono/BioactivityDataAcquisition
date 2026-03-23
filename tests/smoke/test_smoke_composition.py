"""Smoke tests for composition layer import health.

Validates that uncovered composition modules load without ImportError,
catching wiring breakage before the heavier test suite runs.
"""

from __future__ import annotations

import importlib

import pytest

# bootstrap/runtime modules still relying on smoke/import confidence
_BOOTSTRAP_RUNTIME_MODULES: list[str] = []

# factories/pipeline modules still relying on smoke/import confidence
_FACTORY_PIPELINE_MODULES: list[str] = []

# factories/services modules still relying on smoke/import confidence
_FACTORY_SERVICES_MODULES: list[str] = []

# factories/storage modules without dedicated unit coverage
_FACTORY_STORAGE_MODULES = [
    "bioetl.composition.factories.storage._bronze",
    "bioetl.composition.factories.storage._gold",
    "bioetl.composition.factories.storage._silver",
    "bioetl.composition.factories.storage.write_mixin",
    "bioetl.composition.factories.storage.storage_factory",
]

_ALL_COMPOSITION_MODULES = (
    _BOOTSTRAP_RUNTIME_MODULES
    + _FACTORY_PIPELINE_MODULES
    + _FACTORY_SERVICES_MODULES
    + _FACTORY_STORAGE_MODULES
)


@pytest.mark.smoke
class TestCompositionImportHealth:
    """Parametrized import guard for uncovered composition modules."""

    @pytest.mark.parametrize("module_path", _ALL_COMPOSITION_MODULES)
    def test_module_importable(self, module_path: str) -> None:
        """Each composition module must import without errors."""
        importlib.import_module(module_path)
