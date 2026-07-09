"""Unit tests for pipeline bootstrap (composition root entry point)."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.bootstrap.runtime.pipeline import (
    RuntimeBootstrapPhases,
    bootstrap_pipeline_runner,
    build_runtime_bootstrap_phases,
)
from bioetl.composition.runtime_builders.runner_builder_wiring import (
    RunnerBuilderWiring,
)

pytestmark = pytest.mark.repo_backed


@pytest.mark.unit
class TestBootstrapPipelineRunner:
    """Tests for bootstrap_pipeline_runner."""

    def test_returns_pipeline_runner(
        self,
    ) -> None:
        """bootstrap_pipeline_runner returns the runner from build_pipeline_runner."""
        expected_runner = MagicMock()
        ctx = MagicMock()
        ctx.pipeline_name = "chembl_activity"
        ctx.cached_bronze = None
        registry = MagicMock()
        effective_registry = MagicMock()
        configs_root = Path("/tmp/bioetl-configs")
        factory_wiring = MagicMock(name="factory_wiring")
        input_wiring = MagicMock(name="input_wiring")

        with (
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline.apply_runtime_compatibility_patches"
            ) as mock_compatibility,
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline.prepare_runtime_registry",
                return_value=effective_registry,
            ) as mock_prepare_registry,
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline.resolve_configs_root",
                return_value=configs_root,
            ) as mock_resolve_configs_root,
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.initialize_runtime_policy_sources"
            ) as mock_initialize_policy_sources,
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.build_bootstrap_runner_factory_wiring",
                return_value=factory_wiring,
            ) as mock_build_factory_wiring,
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.build_bootstrap_runner_input_wiring",
                return_value=input_wiring,
            ) as mock_build_input_wiring,
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline._build_pipeline_runner",
                return_value=expected_runner,
            ) as mock_build_runner,
        ):
            result = bootstrap_pipeline_runner(ctx, registry=registry)

        assert result is expected_runner
        mock_compatibility.assert_called_once_with()
        mock_prepare_registry.assert_called_once_with(
            registry=registry,
            pipeline_name="chembl_activity",
        )
        mock_resolve_configs_root.assert_called_once_with()
        mock_initialize_policy_sources.assert_called_once_with(configs_root)
        mock_build_factory_wiring.assert_called_once_with()
        mock_build_input_wiring.assert_called_once_with(
            configs_root=configs_root,
            load_pipeline_config_fn=None,
        )
        mock_build_runner.assert_called_once_with(
            ctx=ctx,
            registry=effective_registry,
            wiring=RunnerBuilderWiring(factory=factory_wiring, inputs=input_wiring),
        )

    def test_delegates_missing_registry_to_runtime_registry_phase(self) -> None:
        """Registry creation and registration are owned by prepare_runtime_registry."""
        ctx = MagicMock()
        ctx.pipeline_name = "chembl_activity"
        ctx.cached_bronze = None
        with (
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline.prepare_runtime_registry"
            ) as mock_prepare_registry,
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline.resolve_configs_root",
                return_value=Path("/tmp/bioetl-configs"),
            ),
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.initialize_runtime_policy_sources"
            ),
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.build_bootstrap_runner_factory_wiring"
            ),
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.build_bootstrap_runner_input_wiring"
            ),
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline._build_pipeline_runner"
            ),
        ):
            bootstrap_pipeline_runner(ctx, registry=None)

        mock_prepare_registry.assert_called_once_with(
            registry=None,
            pipeline_name="chembl_activity",
        )

    def test_prefers_explicit_pipeline_loader_injection_over_bound_loader_factory(
        self,
    ) -> None:
        """Bootstrap should use explicit injected loader instead of identity checks."""
        configs_root = Path("/tmp/bioetl-configs")
        ctx = MagicMock()
        ctx.pipeline_name = "chembl_activity"
        ctx.cached_bronze = None
        injected_loader = MagicMock(name="injected_pipeline_loader")

        with (
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline.prepare_runtime_registry",
                return_value=MagicMock(),
            ),
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline.resolve_configs_root",
                return_value=configs_root,
            ),
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.initialize_runtime_policy_sources"
            ),
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.build_bootstrap_runner_factory_wiring"
            ),
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.build_bootstrap_runner_input_wiring"
            ) as mock_build_input_wiring,
            patch(
                "bioetl.composition.bootstrap.runtime.pipeline._build_pipeline_runner"
            ),
        ):
            bootstrap_pipeline_runner(
                ctx,
                registry=MagicMock(),
                load_pipeline_config_fn=injected_loader,
            )

        mock_build_input_wiring.assert_called_once_with(
            configs_root=configs_root,
            load_pipeline_config_fn=injected_loader,
        )


def test_build_runtime_bootstrap_phases_returns_typed_payload() -> None:
    """Runtime bootstrap phases must be explicit before runner construction."""
    ctx = MagicMock()
    ctx.pipeline_name = "chembl_activity"
    ctx.cached_bronze = None
    registry = MagicMock(name="registry")
    effective_registry = MagicMock(name="effective_registry")
    configs_root = Path("/tmp/bioetl-configs")
    factory_wiring = MagicMock(name="factory_wiring")
    input_wiring = MagicMock(name="input_wiring")
    injected_loader = MagicMock(name="injected_pipeline_loader")

    with (
        patch(
            "bioetl.composition.bootstrap.runtime.pipeline.apply_runtime_compatibility_patches"
        ) as mock_compatibility,
        patch(
            "bioetl.composition.bootstrap.runtime.pipeline.prepare_runtime_registry",
            return_value=effective_registry,
        ) as mock_prepare_registry,
        patch(
            "bioetl.composition.bootstrap.runtime.pipeline.resolve_configs_root",
            return_value=configs_root,
        ),
        patch(
            "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.initialize_runtime_policy_sources"
        ) as mock_initialize_policy_sources,
        patch(
            "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.build_bootstrap_runner_factory_wiring",
            return_value=factory_wiring,
        ),
        patch(
            "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases.build_bootstrap_runner_input_wiring",
            return_value=input_wiring,
        ) as mock_build_input_wiring,
    ):
        phases = build_runtime_bootstrap_phases(
            ctx=ctx,
            registry=registry,
            load_pipeline_config_fn=injected_loader,
        )

    assert isinstance(phases, RuntimeBootstrapPhases)
    assert phases.registry is effective_registry
    assert phases.configs_root == configs_root
    assert phases.factory_wiring is factory_wiring
    assert phases.input_wiring is input_wiring
    assert phases.wiring == RunnerBuilderWiring(
        factory=factory_wiring,
        inputs=input_wiring,
    )
    mock_compatibility.assert_called_once_with()
    mock_prepare_registry.assert_called_once_with(
        registry=registry,
        pipeline_name="chembl_activity",
    )
    mock_initialize_policy_sources.assert_called_once_with(configs_root)
    mock_build_input_wiring.assert_called_once_with(
        configs_root=configs_root,
        load_pipeline_config_fn=injected_loader,
    )


def test_pipeline_bootstrap_uses_runtime_phase_helpers() -> None:
    """Runtime bootstrap should route config loading through phase helpers."""
    source = Path("src/bioetl/composition/bootstrap/runtime/pipeline.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert (
        "bioetl.composition.bootstrap.runtime.pipeline_bootstrap_phases"
        in imported_modules
    ), (
        "bootstrap runtime pipeline must delegate config and registry wiring "
        "through pipeline_bootstrap_phases."
    )
    assert "bioetl.infrastructure.config.pipeline_config_api" not in imported_modules, (
        "bootstrap runtime pipeline must not import pipeline_config_api directly."
    )
