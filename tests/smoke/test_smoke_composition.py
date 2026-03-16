"""Smoke tests for composition layer import health.

Validates that uncovered composition modules load without ImportError,
catching wiring breakage before the heavier test suite runs.
"""
from __future__ import annotations

import importlib

import pytest

# bootstrap/runtime modules without dedicated unit coverage
_BOOTSTRAP_RUNTIME_MODULES = [
    "bioetl.composition.bootstrap.runtime.runtime_basics",
    "bioetl.composition.bootstrap.runtime.pipeline",
    "bioetl.composition.bootstrap.runtime.runner_assembly",
    "bioetl.composition.bootstrap.runtime.observability_bundle",
]

# factories/pipeline modules without dedicated unit coverage
_FACTORY_PIPELINE_MODULES = [
    "bioetl.composition.factories.pipeline.assembler",
    "bioetl.composition.factories.pipeline.contract_validator",
    "bioetl.composition.factories.pipeline._creation_wiring",
    "bioetl.composition.factories.pipeline.factory_method_helpers",
    "bioetl.composition.factories.pipeline.config_types",
    "bioetl.composition.factories.pipeline.runner_assembly",
    "bioetl.composition.factories.pipeline.transformer_dependencies",
]

# factories/services modules without dedicated unit coverage
_FACTORY_SERVICES_MODULES = [
    "bioetl.composition.factories.services.builder",
    "bioetl.composition.factories.services.common_service_wiring",
    "bioetl.composition.factories.services.pipeline_builder",
    "bioetl.composition.factories.services.pipeline_processing",
    "bioetl.composition.factories.services.runtime_managers",
]

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
