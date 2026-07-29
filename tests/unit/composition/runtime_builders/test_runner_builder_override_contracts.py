"""Runner-builder override and lazy-resolution contracts."""

import inspect
import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from bioetl.composition.runtime_builders import inputs_runtime_assembly
from bioetl.composition.runtime_builders import runner_builder
from bioetl.composition.runtime_builders import runner_builder_wiring
from bioetl.composition.runtime_builders import runner_input_assembly


pytestmark = pytest.mark.unit


def test_runner_input_assembly_lazy_resolves_default_observability_builder(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_module = ModuleType(
        "bioetl.composition.runtime_builders.observability_builder"
    )
    build_observability_bundle = MagicMock(name="build_observability_bundle")
    fake_module.build_observability_bundle = build_observability_bundle
    monkeypatch.setitem(
        sys.modules,
        "bioetl.composition.runtime_builders.observability_builder",
        fake_module,
    )
    resolved = runner_input_assembly._resolve_optional_functions(
        build_observability_bundle_fn=None,
        assemble_vacuum_settings_fn=None,
        assemble_runtime_config_fn=None,
        assemble_filter_config_fn=None,
        assemble_cached_bronze_context_fn=None,
    )
    assert resolved[0] is build_observability_bundle
    assert resolved[1] is inputs_runtime_assembly.assemble_vacuum_settings
    assert resolved[2] is inputs_runtime_assembly.assemble_runtime_config
    assert resolved[3] is inputs_runtime_assembly.assemble_filter_config
    assert resolved[4] is inputs_runtime_assembly.assemble_cached_bronze_context


def test_runner_builder_wiring_applies_legacy_overrides_without_mutating_base() -> None:
    base = runner_builder_wiring.RunnerBuilderWiring()
    create_registry = MagicMock(name="create_registry")
    load_pipeline_config = MagicMock(name="load_pipeline_config")
    resolved = runner_builder_wiring.resolve_runner_builder_wiring(
        base,
        legacy_overrides=runner_builder_wiring.LegacyRunnerBuilderOverrides(
            create_registry_fn=create_registry,
            load_pipeline_config_fn=load_pipeline_config,
        ),
    )
    assert resolved is not base
    assert resolved.factory.create_registry is create_registry
    assert resolved.inputs.load_pipeline_config is load_pipeline_config
    assert base.factory.create_registry is not create_registry
    assert base.inputs.load_pipeline_config is not load_pipeline_config


def test_build_pipeline_runner_override_surface_is_capped() -> None:
    """Ad hoc builder injection must not grow outside the typed wiring seam."""
    params = inspect.signature(runner_builder.build_pipeline_runner).parameters
    legacy_override_names = {name for name in params if name.endswith("_fn")}
    assert "wiring" in params
    assert "legacy_overrides" not in params
    assert "factory_wiring" not in params
    assert "input_wiring" not in params
    assert legacy_override_names == set()


def test_runner_input_wiring_applies_legacy_overrides_without_mutating_base() -> None:
    base = runner_builder_wiring.RunnerInputWiring()
    load_pipeline_config = MagicMock(name="load_pipeline_config")
    resolved = runner_builder_wiring.resolve_runner_input_wiring(
        base,
        load_pipeline_config_fn=load_pipeline_config,
    )
    assert resolved is not base
    assert resolved.load_pipeline_config is load_pipeline_config
    assert base.load_pipeline_config is not load_pipeline_config
