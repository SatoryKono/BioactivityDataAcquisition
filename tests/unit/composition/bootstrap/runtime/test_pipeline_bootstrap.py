"""Unit tests for pipeline bootstrap (composition root entry point)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.bootstrap.runtime.pipeline import bootstrap_pipeline_runner


@pytest.mark.unit
class TestBootstrapPipelineRunner:
    """Tests for bootstrap_pipeline_runner."""

    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_publication_type_classification"
    )
    @patch("bioetl.composition.bootstrap.runtime.pipeline.ProviderRegistry")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.register_all_pipelines")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.build_pipeline_runner")
    def test_returns_pipeline_runner(
        self,
        mock_build_runner: MagicMock,
        mock_register: MagicMock,
        mock_provider_registry: MagicMock,
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
    @patch("bioetl.composition.bootstrap.runtime.pipeline.ProviderRegistry")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.register_all_pipelines")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.build_pipeline_runner")
    def test_skips_registration_when_pipelines_exist(
        self,
        mock_build_runner: MagicMock,
        mock_register: MagicMock,
        mock_provider_registry: MagicMock,
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
    @patch("bioetl.composition.bootstrap.runtime.pipeline.ProviderRegistry")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.register_all_pipelines")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.build_pipeline_runner")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.create_registry")
    def test_creates_registry_when_none_provided(
        self,
        mock_create_registry: MagicMock,
        mock_build_runner: MagicMock,
        mock_register: MagicMock,
        mock_provider_registry: MagicMock,
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
    @patch("bioetl.composition.bootstrap.runtime.pipeline.ProviderRegistry")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.register_all_pipelines")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.build_pipeline_runner")
    def test_calls_classification_init(
        self,
        mock_build_runner: MagicMock,
        mock_register: MagicMock,
        mock_provider_registry: MagicMock,
        mock_classify: MagicMock,
    ) -> None:
        """Classification initialization is called before pipeline registration."""
        mock_build_runner.return_value = MagicMock()
        registry = MagicMock()
        registry.list_pipelines.return_value = ["p"]

        bootstrap_pipeline_runner(MagicMock(), registry=registry)

        mock_classify.assert_called_once()

    @patch(
        "bioetl.composition.bootstrap.runtime.pipeline.initialize_publication_type_classification"
    )
    @patch("bioetl.composition.bootstrap.runtime.pipeline.ProviderRegistry")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.register_all_pipelines")
    @patch("bioetl.composition.bootstrap.runtime.pipeline.build_pipeline_runner")
    def test_ensures_providers_loaded(
        self,
        mock_build_runner: MagicMock,
        mock_register: MagicMock,
        mock_provider_registry: MagicMock,
        mock_classify: MagicMock,
    ) -> None:
        """ProviderRegistry.ensure_loaded is always called."""
        mock_build_runner.return_value = MagicMock()
        registry = MagicMock()
        registry.list_pipelines.return_value = ["p"]

        bootstrap_pipeline_runner(MagicMock(), registry=registry)

        mock_provider_registry.ensure_loaded.assert_called_once()
