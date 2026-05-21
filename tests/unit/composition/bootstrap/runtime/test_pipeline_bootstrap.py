"""Unit tests for pipeline bootstrap (composition root entry point)."""

from __future__ import annotations

import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner

pytestmark = pytest.mark.repo_backed


@pytest.mark.unit
class TestBootstrapPipelineRunner:
    """Tests for bootstrap_pipeline_runner."""

    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_publication_type_classification"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_chembl_policy_registry"
    )
    @patch("bioetl.composition.bootstrap.runtime.pipeline.ensure_providers_loaded")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.register_all_pipelines")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.build_pipeline_runner")
    def test_returns_pipeline_runner(
        self,
        mock_build_runner: MagicMock,
        mock_register: MagicMock,
        mock_ensure_providers_loaded: MagicMock,
        mock_init_chembl_policy: MagicMock,
        mock_classify: MagicMock,
    ) -> None:
        """bootstrap_pipeline_runner returns the runner from build_pipeline_runner."""
        expected_runner = MagicMock()
        mock_build_runner.return_value = expected_runner
        ctx = MagicMock()

        # Registry with no pipelines triggers registration
        registry = MagicMock()
        registry.list_pipelines.return_value = []

        result = bootstrap_pipeline_runner(ctx, registry=registry)

        assert result is expected_runner
        mock_build_runner.assert_called_once()

    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_publication_type_classification"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_chembl_policy_registry"
    )
    @patch("bioetl.composition.bootstrap.runtime.pipeline.ensure_providers_loaded")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.register_all_pipelines")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.build_pipeline_runner")
    def test_skips_registration_when_pipelines_exist(
        self,
        mock_build_runner: MagicMock,
        mock_register: MagicMock,
        mock_ensure_providers_loaded: MagicMock,
        mock_init_chembl_policy: MagicMock,
        mock_classify: MagicMock,
    ) -> None:
        """When registry already has pipelines, register_all_pipelines is not called."""
        mock_build_runner.return_value = MagicMock()
        registry = MagicMock()
        registry.list_pipelines.return_value = ["chembl_activity"]

        bootstrap_pipeline_runner(MagicMock(), registry=registry)

        mock_register.assert_not_called()

    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_publication_type_classification"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_chembl_policy_registry"
    )
    @patch("bioetl.composition.bootstrap.runtime.pipeline.ensure_providers_loaded")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.register_all_pipelines")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.build_pipeline_runner")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.create_registry")
    def test_creates_registry_when_none_provided(
        self,
        mock_create_registry: MagicMock,
        mock_build_runner: MagicMock,
        mock_register: MagicMock,
        mock_ensure_providers_loaded: MagicMock,
        mock_init_chembl_policy: MagicMock,
        mock_classify: MagicMock,
    ) -> None:
        """When no registry is provided, create_registry() is used."""
        new_registry = MagicMock()
        new_registry.list_pipelines.return_value = []
        mock_create_registry.return_value = new_registry
        mock_build_runner.return_value = MagicMock()

        bootstrap_pipeline_runner(MagicMock(), registry=None)

        mock_create_registry.assert_called_once()

    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_publication_type_classification"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_chembl_policy_registry"
    )
    @patch("bioetl.composition.bootstrap.runtime.pipeline.ensure_providers_loaded")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.register_all_pipelines")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.build_pipeline_runner")
    def test_calls_classification_init(
        self,
        mock_build_runner: MagicMock,
        mock_register: MagicMock,
        mock_ensure_providers_loaded: MagicMock,
        mock_init_chembl_policy: MagicMock,
        mock_classify: MagicMock,
    ) -> None:
        """Classification initialization is called before pipeline registration."""
        mock_build_runner.return_value = MagicMock()
        registry = MagicMock()
        registry.list_pipelines.return_value = ["p"]

        bootstrap_pipeline_runner(MagicMock(), registry=registry)

        mock_init_chembl_policy.assert_called_once()
        mock_classify.assert_called_once()

    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_publication_type_classification"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_chembl_policy_registry"
    )
    @patch("bioetl.composition.bootstrap.runtime.pipeline.ensure_providers_loaded")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.register_all_pipelines")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.build_pipeline_runner")
    def test_ensures_providers_loaded(
        self,
        mock_build_runner: MagicMock,
        mock_register: MagicMock,
        mock_ensure_providers_loaded: MagicMock,
        mock_init_chembl_policy: MagicMock,
        mock_classify: MagicMock,
    ) -> None:
        """Runtime provider bootstrap helper is always called."""
        mock_build_runner.return_value = MagicMock()
        registry = MagicMock()
        registry.list_pipelines.return_value = ["p"]

        bootstrap_pipeline_runner(MagicMock(), registry=registry)

        mock_ensure_providers_loaded.assert_called_once_with()

    @patch("bioetl.composition.bootstrap.runtime.pipeline.create_source_config_loader")
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.create_pipeline_config_loader"
    )
    @patch("bioetl.composition.bootstrap.runtime.pipeline.resolve_configs_root")
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_publication_controlled_vocabulary"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_publication_type_classification"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_chembl_policy_registry"
    )
    @patch("bioetl.composition.bootstrap.runtime.pipeline.ensure_providers_loaded")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.register_all_pipelines")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.build_pipeline_runner")
    def test_uses_resolved_configs_root_for_runtime_initialization_and_loaders(
        self,
        mock_build_runner: MagicMock,
        mock_register: MagicMock,
        mock_ensure_providers_loaded: MagicMock,
        mock_init_chembl_policy: MagicMock,
        mock_classify: MagicMock,
        mock_init_publication_vocab: MagicMock,
        mock_resolve_configs_root: MagicMock,
        mock_create_pipeline_loader: MagicMock,
        mock_create_source_loader: MagicMock,
    ) -> None:
        """Runtime bootstrap should bind loaders and init data to one config root."""
        configs_root = Path("/tmp/bioetl-configs")
        registry = MagicMock()
        registry.list_pipelines.return_value = ["chembl_activity"]
        mock_build_runner.return_value = MagicMock()
        mock_resolve_configs_root.return_value = configs_root
        pipeline_loader = MagicMock(name="pipeline_loader")
        source_loader = MagicMock(name="source_loader")
        mock_create_pipeline_loader.return_value = pipeline_loader
        mock_create_source_loader.return_value = source_loader

        bootstrap_pipeline_runner(MagicMock(), registry=registry)

        mock_resolve_configs_root.assert_called_once_with()
        mock_init_chembl_policy.assert_called_once_with(configs_root)
        mock_classify.assert_called_once_with(configs_root)
        mock_init_publication_vocab.assert_called_once_with(configs_root)
        mock_create_pipeline_loader.assert_called_once_with(configs_root)
        mock_create_source_loader.assert_called_once_with(configs_root)
        build_kwargs = mock_build_runner.call_args.kwargs
        assert build_kwargs["load_pipeline_config_fn"] is pipeline_loader
        assert build_kwargs["load_source_config_fn"] is source_loader

    @patch("bioetl.composition.bootstrap.runtime.pipeline.create_source_config_loader")
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.create_pipeline_config_loader"
    )
    @patch("bioetl.composition.bootstrap.runtime.pipeline.resolve_configs_root")
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_publication_controlled_vocabulary"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_publication_type_classification"
    )
    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_chembl_policy_registry"
    )
    @patch("bioetl.composition.bootstrap.runtime.pipeline.ensure_providers_loaded")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.register_all_pipelines")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.build_pipeline_runner")
    def test_prefers_explicit_pipeline_loader_injection_over_bound_loader_factory(
        self,
        mock_build_runner: MagicMock,
        mock_register: MagicMock,
        mock_ensure_providers_loaded: MagicMock,
        mock_init_chembl_policy: MagicMock,
        mock_classify: MagicMock,
        mock_init_publication_vocab: MagicMock,
        mock_resolve_configs_root: MagicMock,
        mock_create_pipeline_loader: MagicMock,
        mock_create_source_loader: MagicMock,
    ) -> None:
        """Bootstrap should use explicit injected loader instead of identity checks."""
        configs_root = Path("/tmp/bioetl-configs")
        registry = MagicMock()
        registry.list_pipelines.return_value = ["chembl_activity"]
        mock_build_runner.return_value = MagicMock()
        mock_resolve_configs_root.return_value = configs_root
        injected_loader = MagicMock(name="injected_pipeline_loader")
        source_loader = MagicMock(name="source_loader")
        mock_create_pipeline_loader.return_value = MagicMock(name="default_loader")
        mock_create_source_loader.return_value = source_loader

        bootstrap_pipeline_runner(
            MagicMock(),
            registry=registry,
            load_pipeline_config_fn=injected_loader,
        )

        build_kwargs = mock_build_runner.call_args.kwargs
        assert build_kwargs["load_pipeline_config_fn"] is injected_loader
        mock_create_pipeline_loader.assert_not_called()
        mock_init_publication_vocab.assert_called_once_with(configs_root)


def test_pipeline_bootstrap_uses_runtime_config_access_seam() -> None:
    """Runtime bootstrap should route config loading through the local seam."""
    source = Path("src/bioetl/composition/bootstrap/runtime/pipeline.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)

    imported_modules = {
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "bioetl.composition.runtime_builders.config_access" in imported_modules, (
        "bootstrap runtime pipeline must use the runtime config_access seam."
    )
    assert "bioetl.infrastructure.config.pipeline_config_api" not in imported_modules, (
        "bootstrap runtime pipeline must not import pipeline_config_api directly."
    )
