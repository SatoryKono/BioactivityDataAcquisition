"""Factory overrides preserve collaborators outside the requested replacement."""

from unittest.mock import MagicMock

import pytest

from bioetl.composition.runtime_builders import runner_builder_wiring

pytestmark = pytest.mark.unit


def test_runner_factory_wiring_preserves_unmodified_collaborators() -> None:
    original = runner_builder_wiring.RunnerFactoryWiring()
    ensure_providers_loaded = MagicMock(name="ensure_providers_loaded")
    register_all_pipelines = MagicMock(name="register_all_pipelines")
    resolved = runner_builder_wiring.resolve_runner_factory_wiring(
        original,
        ensure_providers_loaded_fn=ensure_providers_loaded,
        register_all_pipelines_fn=register_all_pipelines,
    )
    assert resolved is not original
    assert resolved.create_registry is original.create_registry
    assert resolved.ensure_providers_loaded is ensure_providers_loaded
    assert resolved.register_all_pipelines is register_all_pipelines
