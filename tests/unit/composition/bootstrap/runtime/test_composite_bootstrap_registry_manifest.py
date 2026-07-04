"""Unit tests for composite bootstrap registry manifest."""

from __future__ import annotations

import importlib

import pytest

from bioetl.composition.bootstrap.runtime.composite_bootstrap_registry_manifest import (
    COMPOSITE_BOOTSTRAP_BUILDER_MODULES,
    COMPOSITE_BOOTSTRAP_BUNDLE_MODULES,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize("module_path", COMPOSITE_BOOTSTRAP_BUILDER_MODULES.values())
def test_composite_bootstrap_builder_modules_are_importable(module_path: str) -> None:
    module = importlib.import_module(module_path)
    assert module.__name__ == module_path


@pytest.mark.parametrize("module_path", COMPOSITE_BOOTSTRAP_BUNDLE_MODULES.values())
def test_composite_bootstrap_bundle_modules_are_importable(module_path: str) -> None:
    module = importlib.import_module(module_path)
    assert module.__name__ == module_path
