"""Structural contract tests for runtime runner builder seams."""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from bioetl.composition.runtime_builders import inputs_resolver
from bioetl.composition.runtime_builders import runner_builder
from bioetl.composition.runtime_builders import runner_control_plane_assembly
from bioetl.composition.runtime_builders import runner_input_assembly
from bioetl.composition.runtime_builders import runner_builder_wiring

pytestmark = pytest.mark.unit


def test_runner_builder_uses_runtime_config_access_seam() -> None:
    source = Path(
        "src/bioetl/composition/runtime_builders/runner_builder.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "bioetl.composition.runtime_builders.config_access" in imported_modules, (
        "runner_builder must use the runtime config_access seam."
    )
    assert "bioetl.infrastructure.config.pipeline_config_api" not in imported_modules, (
        "runner_builder must not import pipeline_config_api directly."
    )
    assert (
        "bioetl.infrastructure.config.source_config_loader" not in imported_modules
    ), "runner_builder must not import source_config_loader directly."


def test_runner_builder_does_not_expose_legacy_wrapper_patch_points() -> None:
    for attr_name in (
        "VacuumSettings",
        "_assemble_vacuum_settings",
        "_assemble_runtime_config",
        "_assemble_filter_config",
        "_assemble_cached_bronze_context",
        "_build_observability_bundle",
        "_validate_pk_contract",
        "_resolve_health_check_mode",
        "_resolve_filter_batch_size",
        "build_observability_bundle",
        "assemble_vacuum_settings",
        "assemble_runtime_config",
        "assemble_filter_config",
        "assemble_cached_bronze_context",
    ):
        assert not hasattr(runner_builder, attr_name)


def test_runner_builder_uses_dedicated_control_plane_assembler() -> None:
    assert hasattr(runner_control_plane_assembly, "ControlPlaneSetupResult")
    assert hasattr(runner_control_plane_assembly, "assemble_runner_control_plane")
    assert not hasattr(runner_builder, "_ControlPlaneSetupResult")
    assert not hasattr(runner_builder, "_handle_control_plane_setup")


def test_inputs_resolver_uses_explicit_resolved_vacuumsettings_name() -> None:
    assert hasattr(inputs_resolver, "ResolvedVacuumSettings")
    assert not hasattr(inputs_resolver, "VacuumSettings")


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
    assert resolved[1] is inputs_resolver.assemble_vacuum_settings
    assert resolved[2] is inputs_resolver.assemble_runtime_config
    assert resolved[3] is inputs_resolver.assemble_filter_config
    assert resolved[4] is inputs_resolver.assemble_cached_bronze_context


def test_runner_builder_exposes_typed_wiring_bundles() -> None:
    """Runtime builder fan-in should be grouped behind typed wiring bundles."""
    assert hasattr(runner_builder, "RunnerFactoryWiring")
    assert hasattr(runner_builder, "RunnerInputWiring")

    create_registry = MagicMock(name="create_registry")
    wiring = runner_builder_wiring.resolve_runner_factory_wiring(
        runner_builder_wiring.RunnerFactoryWiring(),
        create_registry_fn=create_registry,
    )

    assert wiring.create_registry is create_registry
    assert callable(wiring.ensure_providers_loaded)
    assert callable(wiring.register_all_pipelines)


def test_runner_input_wiring_applies_legacy_overrides_without_mutating_base() -> None:
    """Legacy keyword patch points must resolve into one immutable bundle."""
    base = runner_builder_wiring.RunnerInputWiring()
    load_pipeline_config = MagicMock(name="load_pipeline_config")

    resolved = runner_builder_wiring.resolve_runner_input_wiring(
        base,
        load_pipeline_config_fn=load_pipeline_config,
    )

    assert resolved is not base
    assert resolved.load_pipeline_config is load_pipeline_config
    assert base.load_pipeline_config is not load_pipeline_config
