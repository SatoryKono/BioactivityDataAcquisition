"""Unit tests for retired application/core wiring API facades."""

from __future__ import annotations

import importlib

import pytest


pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "module_name",
    [
        "bioetl.application.core.pipeline_registry_wiring_api",
        "bioetl.application.core.runtime_wiring_api",
        "bioetl.application.core.transformer_wiring_api",
    ],
)
def test_legacy_wiring_api_facades_stay_removed(module_name: str) -> None:
    """Legacy flat wiring facades must not be reintroduced."""
    with pytest.raises(ModuleNotFoundError):
        importlib.import_module(module_name)


def test_canonical_wiring_owner_modules_remain_importable() -> None:
    """The split owner modules remain the supported first-party import paths."""
    from bioetl.application.core.wiring.factory import PipelineRunner
    from bioetl.application.core.wiring.registry import ActivityTransformer
    from bioetl.application.core.wiring.transformer import BaseTransformer

    assert isinstance(ActivityTransformer, type)
    assert isinstance(PipelineRunner, type)
    assert isinstance(BaseTransformer, type)
