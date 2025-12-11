"""Tests for RunPipelineUseCase."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from bioetl.application.use_cases import (
    InterfaceDisabledError,
    RunPipelineRequest,
    RunPipelineResponse,
    RunPipelineUseCase,
)
from bioetl.domain.value_objects import RunId


class TestRunPipelineRequest:
    """Tests for RunPipelineRequest dataclass."""

    def test_default_values(self) -> None:
        """Test that request has sensible defaults."""
        request = RunPipelineRequest(pipeline_name="activity_chembl")

        assert request.pipeline_name == "activity_chembl"
        assert request.profile == "default"
        assert request.dry_run is False
        assert request.limit is None
        assert request.config_path is None
        assert request.output_path is None
        assert request.require_rest_interface is False

    def test_get_pipeline_id_with_entity_provider_format(self) -> None:
        """Test pipeline ID extraction from entity_provider format."""
        request = RunPipelineRequest(pipeline_name="activity_chembl")
        assert request.get_pipeline_id() == "chembl.activity"

    def test_get_pipeline_id_with_multiple_underscores(self) -> None:
        """Test pipeline ID extraction with multiple underscores."""
        request = RunPipelineRequest(pipeline_name="drug_indication_chembl")
        assert request.get_pipeline_id() == "chembl.drug_indication"

    def test_get_pipeline_id_without_underscore(self) -> None:
        """Test pipeline ID fallback for names without underscore."""
        request = RunPipelineRequest(pipeline_name="activity")
        assert request.get_pipeline_id() == "chembl.activity"

    def test_is_frozen(self) -> None:
        """Test that request is immutable."""
        request = RunPipelineRequest(pipeline_name="activity_chembl")

        with pytest.raises(Exception):  # FrozenInstanceError
            request.pipeline_name = "other"  # type: ignore

    def test_all_fields_can_be_set(self) -> None:
        """Test that all fields can be set in constructor."""
        request = RunPipelineRequest(
            pipeline_name="activity_chembl",
            profile="production",
            dry_run=True,
            limit=100,
            config_path=Path("/some/config.yaml"),
            output_path=Path("/some/output"),
            require_rest_interface=True,
        )

        assert request.pipeline_name == "activity_chembl"
        assert request.profile == "production"
        assert request.dry_run is True
        assert request.limit == 100
        assert request.config_path == Path("/some/config.yaml")
        assert request.output_path == Path("/some/output")
        assert request.require_rest_interface is True


class TestRunPipelineResponse:
    """Tests for RunPipelineResponse dataclass."""

    def test_default_errors(self) -> None:
        """Test that errors default to empty list."""
        response = RunPipelineResponse(
            run_id="12345678-1234-1234-1234-123456789abc",
            success=True,
            row_count=100,
            duration_sec=1.5,
            output_path=None,
        )

        assert response.errors == []

    def test_from_run_result(self) -> None:
        """Test creation from RunResult."""
        # Create a mock RunResult
        run_result = Mock()
        run_result.run_id = RunId("12345678-1234-1234-1234-123456789abc")
        run_result.success = True
        run_result.row_count = 100
        run_result.duration_sec = 1.5
        run_result.output_path = Path("/output/data.parquet")
        run_result.errors = ["warning1", "warning2"]

        response = RunPipelineResponse.from_run_result(run_result)

        assert response.run_id == "12345678-1234-1234-1234-123456789abc"
        assert response.success is True
        assert response.row_count == 100
        assert response.duration_sec == 1.5
        assert response.output_path == Path("/output/data.parquet")
        assert response.errors == ["warning1", "warning2"]

    def test_is_frozen(self) -> None:
        """Test that response is immutable."""
        response = RunPipelineResponse(
            run_id="12345678-1234-1234-1234-123456789abc",
            success=True,
            row_count=100,
            duration_sec=1.5,
            output_path=None,
        )

        with pytest.raises(Exception):  # FrozenInstanceError
            response.success = False  # type: ignore


class TestInterfaceDisabledError:
    """Tests for InterfaceDisabledError."""

    def test_error_message(self) -> None:
        """Test error message format."""
        error = InterfaceDisabledError("REST")
        assert str(error) == "REST interface is disabled by configuration"
        assert error.interface == "REST"

    def test_is_exception(self) -> None:
        """Test that it's a proper exception."""
        error = InterfaceDisabledError("MQ")
        assert isinstance(error, Exception)


class TestRunPipelineUseCase:
    """Tests for RunPipelineUseCase."""

    @pytest.fixture
    def mock_config_loader(self) -> Mock:
        """Create mock config loader."""
        loader = Mock()
        return loader

    @pytest.fixture
    def mock_container_factory(self) -> Mock:
        """Create mock container factory."""
        return Mock()

    @pytest.fixture
    def mock_provider_loader_factory(self) -> Mock:
        """Create mock provider loader factory."""
        return Mock()

    @pytest.fixture
    def mock_provider_registry_factory(self) -> Mock:
        """Create mock provider registry factory."""
        return Mock()

    @pytest.fixture
    def mock_config(self) -> Mock:
        """Create mock PipelineConfig."""
        config = Mock()
        config.features.rest_interface_enabled = True
        config.features.mq_interface_enabled = False
        config.sink.output_path = "/default/output"
        config.sink.model_copy.return_value = config.sink
        config.model_copy.return_value = config
        return config

    @pytest.fixture
    def mock_run_result(self) -> Mock:
        """Create mock RunResult."""
        result = Mock()
        result.run_id = RunId("12345678-1234-1234-1234-123456789abc")
        result.success = True
        result.row_count = 100
        result.duration_sec = 1.5
        result.output_path = Path("/output/data.parquet")
        result.errors = []
        return result

    def test_execute_with_config_path(
        self,
        mock_config_loader: Mock,
        mock_container_factory: Mock,
        mock_provider_loader_factory: Mock,
        mock_provider_registry_factory: Mock,
        mock_config: Mock,
        mock_run_result: Mock,
    ) -> None:
        """Test execute loads config from path when provided."""
        mock_config_loader.get_from_path.return_value = mock_config

        use_case = RunPipelineUseCase(
            config_loader=mock_config_loader,
            container_factory=mock_container_factory,
            provider_loader_factory=mock_provider_loader_factory,
            provider_registry_factory=mock_provider_registry_factory,
            configs_root=Path("/configs"),
        )

        request = RunPipelineRequest(
            pipeline_name="activity_chembl",
            config_path=Path("/custom/config.yaml"),
            profile="production",
        )

        with patch.object(use_case, "_create_orchestrator") as mock_create_orchestrator:
            mock_orchestrator = Mock()
            mock_orchestrator.run_pipeline.return_value = mock_run_result
            mock_create_orchestrator.return_value = mock_orchestrator

            response = use_case.execute(request)

        mock_config_loader.get_from_path.assert_called_once_with(
            Path("/custom/config.yaml"),
            profile="production",
            profiles_root=Path("/configs/profiles"),
        )
        assert response.success is True

    def test_execute_with_pipeline_id(
        self,
        mock_config_loader: Mock,
        mock_container_factory: Mock,
        mock_provider_loader_factory: Mock,
        mock_provider_registry_factory: Mock,
        mock_config: Mock,
        mock_run_result: Mock,
    ) -> None:
        """Test execute loads config by ID when no path provided."""
        mock_config_loader.get_by_id.return_value = mock_config

        use_case = RunPipelineUseCase(
            config_loader=mock_config_loader,
            container_factory=mock_container_factory,
            provider_loader_factory=mock_provider_loader_factory,
            provider_registry_factory=mock_provider_registry_factory,
            configs_root=Path("/configs"),
        )

        request = RunPipelineRequest(
            pipeline_name="activity_chembl",
            profile="default",
        )

        with patch.object(use_case, "_create_orchestrator") as mock_create_orchestrator:
            mock_orchestrator = Mock()
            mock_orchestrator.run_pipeline.return_value = mock_run_result
            mock_create_orchestrator.return_value = mock_orchestrator

            response = use_case.execute(request)

        mock_config_loader.get_by_id.assert_called_once_with(
            "chembl.activity",
            profile="default",
            base_dir=Path("/configs"),
        )
        assert response.success is True

    def test_execute_raises_on_rest_interface_disabled(
        self,
        mock_config_loader: Mock,
        mock_container_factory: Mock,
        mock_provider_loader_factory: Mock,
        mock_config: Mock,
    ) -> None:
        """Test execute raises InterfaceDisabledError when REST is disabled."""
        mock_config.features.rest_interface_enabled = False
        mock_config_loader.get_by_id.return_value = mock_config

        use_case = RunPipelineUseCase(
            config_loader=mock_config_loader,
            container_factory=mock_container_factory,
            provider_loader_factory=mock_provider_loader_factory,
        )

        request = RunPipelineRequest(
            pipeline_name="activity_chembl",
            require_rest_interface=True,
        )

        with pytest.raises(InterfaceDisabledError) as exc_info:
            use_case.execute(request)

        assert exc_info.value.interface == "REST"

    def test_execute_succeeds_without_rest_requirement(
        self,
        mock_config_loader: Mock,
        mock_container_factory: Mock,
        mock_provider_loader_factory: Mock,
        mock_config: Mock,
        mock_run_result: Mock,
    ) -> None:
        """Test execute succeeds when REST not required even if disabled."""
        mock_config.features.rest_interface_enabled = False
        mock_config_loader.get_by_id.return_value = mock_config

        use_case = RunPipelineUseCase(
            config_loader=mock_config_loader,
            container_factory=mock_container_factory,
            provider_loader_factory=mock_provider_loader_factory,
        )

        request = RunPipelineRequest(
            pipeline_name="activity_chembl",
            require_rest_interface=False,
        )

        with patch.object(use_case, "_create_orchestrator") as mock_create_orchestrator:
            mock_orchestrator = Mock()
            mock_orchestrator.run_pipeline.return_value = mock_run_result
            mock_create_orchestrator.return_value = mock_orchestrator

            response = use_case.execute(request)

        assert response.success is True

    def test_execute_applies_output_override(
        self,
        mock_config_loader: Mock,
        mock_container_factory: Mock,
        mock_provider_loader_factory: Mock,
        mock_config: Mock,
        mock_run_result: Mock,
        tmp_path: Path,
    ) -> None:
        """Test execute creates output directory and updates config."""
        mock_config_loader.get_by_id.return_value = mock_config

        use_case = RunPipelineUseCase(
            config_loader=mock_config_loader,
            container_factory=mock_container_factory,
            provider_loader_factory=mock_provider_loader_factory,
        )

        output_path = tmp_path / "custom_output"
        request = RunPipelineRequest(
            pipeline_name="activity_chembl",
            output_path=output_path,
        )

        with patch.object(use_case, "_create_orchestrator") as mock_create_orchestrator:
            mock_orchestrator = Mock()
            mock_orchestrator.run_pipeline.return_value = mock_run_result
            mock_create_orchestrator.return_value = mock_orchestrator

            use_case.execute(request)

        assert output_path.exists()
        mock_config.sink.model_copy.assert_called_once()

    def test_execute_passes_dry_run_and_limit(
        self,
        mock_config_loader: Mock,
        mock_container_factory: Mock,
        mock_provider_loader_factory: Mock,
        mock_config: Mock,
        mock_run_result: Mock,
    ) -> None:
        """Test execute passes dry_run and limit to orchestrator."""
        mock_config_loader.get_by_id.return_value = mock_config

        use_case = RunPipelineUseCase(
            config_loader=mock_config_loader,
            container_factory=mock_container_factory,
            provider_loader_factory=mock_provider_loader_factory,
        )

        request = RunPipelineRequest(
            pipeline_name="activity_chembl",
            dry_run=True,
            limit=50,
        )

        with patch.object(use_case, "_create_orchestrator") as mock_create_orchestrator:
            mock_orchestrator = Mock()
            mock_orchestrator.run_pipeline.return_value = mock_run_result
            mock_create_orchestrator.return_value = mock_orchestrator

            use_case.execute(request)

        mock_orchestrator.run_pipeline.assert_called_once_with(
            dry_run=True,
            limit=50,
        )

    def test_create_orchestrator(
        self,
        mock_config_loader: Mock,
        mock_container_factory: Mock,
        mock_provider_loader_factory: Mock,
        mock_config: Mock,
    ) -> None:
        """Test _create_orchestrator creates orchestrator with correct params."""
        use_case = RunPipelineUseCase(
            config_loader=mock_config_loader,
            container_factory=mock_container_factory,
            provider_loader_factory=mock_provider_loader_factory,
        )

        with patch(
            "bioetl.application.use_cases.run_pipeline.PipelineOrchestrator"
        ) as MockOrchestrator:
            use_case._create_orchestrator("activity_chembl", mock_config)

        MockOrchestrator.assert_called_once_with(
            pipeline_name="activity_chembl",
            config=mock_config,
            provider_loader_factory=mock_provider_loader_factory,
            container_factory=mock_container_factory,
        )

    def test_get_profiles_root_with_configs_root(
        self,
        mock_config_loader: Mock,
        mock_container_factory: Mock,
        mock_provider_loader_factory: Mock,
    ) -> None:
        """Test _get_profiles_root returns profiles subdirectory."""
        use_case = RunPipelineUseCase(
            config_loader=mock_config_loader,
            container_factory=mock_container_factory,
            provider_loader_factory=mock_provider_loader_factory,
            configs_root=Path("/configs"),
        )

        assert use_case._get_profiles_root() == Path("/configs/profiles")

    def test_get_profiles_root_without_configs_root(
        self,
        mock_config_loader: Mock,
        mock_container_factory: Mock,
        mock_provider_loader_factory: Mock,
    ) -> None:
        """Test _get_profiles_root returns None without configs_root."""
        use_case = RunPipelineUseCase(
            config_loader=mock_config_loader,
            container_factory=mock_container_factory,
            provider_loader_factory=mock_provider_loader_factory,
        )

        assert use_case._get_profiles_root() is None
