"""Unit tests for factory_method_helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.pipeline.factory_method_helpers import (
    _BuildFactoryServicesRequest,
    _CreateFactoryRunnerRequest,
    _CreatePipelineWithServicesRequest,
    _PipelineFactoryContext,
    build_factory_services,
    create_factory_data_source,
    create_factory_runner,
    create_pipeline_instance_with_services,
    create_transformer_instance,
)


@pytest.mark.unit
class TestCreateTransformerInstance:
    """Tests for create_transformer_instance."""

    def test_returns_none_when_no_class(self) -> None:
        """Returns None when transformer_class is None."""
        result = create_transformer_instance(
            transformer_class=None,
            provider="chembl",
            pipeline_name="chembl_activity",
            extract_entity_type=lambda n: "activity",
        )

        assert result is None

    def test_creates_transformer_when_class_provided(self) -> None:
        """Instantiates transformer class with extracted entity type."""
        transformer_cls = MagicMock()
        expected = MagicMock()
        transformer_cls.return_value = expected

        result = create_transformer_instance(
            transformer_class=transformer_cls,
            provider="chembl",
            pipeline_name="chembl_activity",
            extract_entity_type=lambda n: "activity",
        )

        assert result is expected
        call_kwargs = transformer_cls.call_args[1]
        assert call_kwargs["provider"] == "chembl"
        assert call_kwargs["entity_type"] == "activity"

    @patch(
        "bioetl.composition.factories.pipeline.factory_method_helpers.build_transformer_dependencies"
    )
    def test_builds_dependencies_when_not_provided(
        self, mock_build_deps: MagicMock
    ) -> None:
        """Builds transformer dependencies when dependencies arg is None."""
        mock_build_deps.return_value = MagicMock()
        transformer_cls = MagicMock()

        create_transformer_instance(
            transformer_class=transformer_cls,
            provider="chembl",
            pipeline_name="chembl_activity",
            extract_entity_type=lambda n: "activity",
            dependencies=None,
        )

        mock_build_deps.assert_called_once()

    def test_uses_provided_dependencies(self) -> None:
        """Uses provided dependencies instead of building new ones."""
        deps = MagicMock()
        transformer_cls = MagicMock()

        create_transformer_instance(
            transformer_class=transformer_cls,
            provider="chembl",
            pipeline_name="chembl_activity",
            extract_entity_type=lambda n: "activity",
            dependencies=deps,
        )

        call_kwargs = transformer_cls.call_args[1]
        assert call_kwargs["dependencies"] is deps


@pytest.mark.unit
class TestCreateFactoryDataSource:
    """Tests for create_factory_data_source."""

    def test_delegates_to_creator_fn(self) -> None:
        """Delegates to the provided create_data_source_fn."""
        expected_source = MagicMock()
        creator = MagicMock(return_value=expected_source)

        result = create_factory_data_source(
            create_data_source_fn=creator,
            settings=MagicMock(),
            pipeline_config=MagicMock(),
            logger=MagicMock(),
            pipeline_name="test_pipe",
        )

        assert result is expected_source
        creator.assert_called_once()


@pytest.mark.unit
class TestBuildFactoryServices:
    """Tests for build_factory_services."""

    @patch(
        "bioetl.composition.factories.pipeline.factory_method_helpers.build_pipeline_services"
    )
    def test_delegates_to_build_pipeline_services(self, mock_build: MagicMock) -> None:
        """Delegates to the canonical build_pipeline_services function."""
        expected = MagicMock()
        mock_build.return_value = expected

        factory_context = _PipelineFactoryContext(
            pipeline_name="test",
            create_data_source_fn=MagicMock(),
        )
        request = _BuildFactoryServicesRequest(
            settings=MagicMock(),
            logger=MagicMock(),
            config=MagicMock(),
            filter_config=MagicMock(),
            tracer=MagicMock(),
            dq_monitor=MagicMock(),
        )
        result = build_factory_services(
            factory_context=factory_context,
            request=request,
        )

        assert result is expected
        mock_build.assert_called_once_with(
            pipeline_name="test",
            create_data_source_fn=factory_context.create_data_source_fn,
            settings=request.settings,
            logger=request.logger,
            config=request.config,
            filter_config=request.filter_config,
            tracer=request.tracer,
            dq_monitor=request.dq_monitor,
        )


@pytest.mark.unit
class TestCreatePipelineInstanceWithServices:
    """Tests for create_pipeline_instance_with_services."""

    @patch(
        "bioetl.composition.factories.pipeline.factory_method_helpers.create_pipeline_with_services"
    )
    def test_delegates_with_factory_context(
        self,
        mock_create_pipeline_with_services: MagicMock,
    ) -> None:
        """Context-backed helper should unwrap factory wiring into canonical call."""
        expected_pipeline = MagicMock()
        mock_create_pipeline_with_services.return_value = expected_pipeline
        pipeline_class = MagicMock()
        transformer_class = MagicMock()
        create_data_source_fn = MagicMock()
        factory_context = _PipelineFactoryContext(
            pipeline_name="chembl_activity",
            create_data_source_fn=create_data_source_fn,
            pipeline_class=pipeline_class,
            provider="chembl",
            transformer_class=transformer_class,
            pandera_silver_schema=MagicMock(),
        )
        runtime = MagicMock()
        settings = MagicMock()
        logger = MagicMock()
        config = MagicMock()
        filter_config = MagicMock()
        tracer = MagicMock()
        dq_monitor = MagicMock()
        metrics = MagicMock()
        cached_bronze = MagicMock()
        request = _CreatePipelineWithServicesRequest(
            run_id="run-1",
            runtime=runtime,
            settings=settings,
            logger=logger,
            config=config,
            filter_config=filter_config,
            tracer=tracer,
            dq_monitor=dq_monitor,
            metrics=metrics,
            cached_bronze=cached_bronze,
        )

        result = create_pipeline_instance_with_services(
            factory_context=factory_context,
            request=request,
        )

        assert result is expected_pipeline
        # The function now passes parameters as structured objects
        call_kwargs = mock_create_pipeline_with_services.call_args.kwargs
        inputs = call_kwargs["inputs"]

        assert inputs.pipeline_name == "chembl_activity"
        assert inputs.pipeline_class is pipeline_class
        assert inputs.provider == "chembl"
        assert inputs.create_data_source_fn is create_data_source_fn
        assert inputs.transformer_class is transformer_class
        assert inputs.pandera_silver_schema is factory_context.pandera_silver_schema
        assert inputs.request.run_id == request.run_id
        assert inputs.request.runtime is request.runtime
        assert inputs.request.settings is request.settings
        assert inputs.request.logger is request.logger
        assert inputs.request.config is request.config
        assert inputs.request.filter_config is request.filter_config
        assert inputs.request.tracer is request.tracer
        assert inputs.request.dq_monitor is request.dq_monitor
        assert inputs.request.metrics is request.metrics
        assert inputs.request.cached_bronze is request.cached_bronze

    @patch(
        "bioetl.composition.factories.pipeline.factory_method_helpers.create_pipeline_with_services"
    )
    def test_forwards_optional_control_plane_kwargs_only_when_present(
        self,
        mock_create_pipeline_with_services: MagicMock,
    ) -> None:
        """Optional control-plane kwargs should flow through only when provided."""
        factory_context = _PipelineFactoryContext(
            pipeline_name="chembl_activity",
            create_data_source_fn=MagicMock(),
            pipeline_class=MagicMock(),
            provider="chembl",
        )
        request = _CreatePipelineWithServicesRequest(
            run_id="run-1",
            runtime=MagicMock(),
            settings=MagicMock(),
            logger=MagicMock(),
            manifest_id="manifest-123",
            execution_fingerprint="fingerprint-123",
            config_hash="hash-123",
            dq_contract_compatibility_hash="dq-hash-123",
            effective_config_artifact_id="artifact-123",
        )

        create_pipeline_instance_with_services(
            factory_context=factory_context,
            request=request,
        )

        # The function now passes parameters as structured objects
        call_kwargs = mock_create_pipeline_with_services.call_args.kwargs
        inputs = call_kwargs["inputs"]

        assert inputs.request.manifest_id == "manifest-123"
        assert inputs.request.execution_fingerprint == "fingerprint-123"
        assert inputs.request.config_hash == "hash-123"
        assert inputs.request.dq_contract_compatibility_hash == "dq-hash-123"
        assert inputs.request.effective_config_artifact_id == "artifact-123"


@pytest.mark.unit
class TestCreateFactoryRunner:
    """Tests for create_factory_runner."""

    @patch(
        "bioetl.composition.factories.pipeline.factory_method_helpers.load_pipeline_config"
    )
    def test_loads_config_when_not_provided(self, mock_load: MagicMock) -> None:
        """Loads pipeline config from disk when config arg is None."""
        mock_load.return_value = MagicMock()
        create_fn = MagicMock(return_value=MagicMock())
        assemble_fn = MagicMock(return_value=MagicMock())
        settings = SimpleNamespace(env="dev", test_mode=False)
        runtime = SimpleNamespace(strict_gold_validation=True)

        create_factory_runner(
            request=_CreateFactoryRunnerRequest(
                pipeline_name="test",
                silver_schema=None,
                gold_schema=MagicMock(),
                run_id="r1",
                runtime=runtime,
                settings=settings,
                observability=MagicMock(
                    logger=MagicMock(),
                    tracer=MagicMock(),
                    metrics=MagicMock(),
                    dq_monitor=None,
                ),
                config=None,
            ),
            create_with_services_fn=create_fn,
            assemble_runner_fn=assemble_fn,
        )

        mock_load.assert_called_once_with("test")

    def test_uses_provided_config(self) -> None:
        """Uses provided config instead of loading from disk."""
        yaml_config = MagicMock()
        create_fn = MagicMock(return_value=MagicMock())
        assemble_fn = MagicMock(return_value=MagicMock())
        settings = SimpleNamespace(env="dev", test_mode=False)
        runtime = SimpleNamespace(strict_gold_validation=True)

        create_factory_runner(
            request=_CreateFactoryRunnerRequest(
                pipeline_name="test",
                silver_schema=None,
                gold_schema=MagicMock(),
                run_id="r1",
                runtime=runtime,
                settings=settings,
                observability=MagicMock(
                    logger=MagicMock(),
                    tracer=MagicMock(),
                    metrics=MagicMock(),
                    dq_monitor=None,
                ),
                config=yaml_config,
            ),
            create_with_services_fn=create_fn,
            assemble_runner_fn=assemble_fn,
        )

        create_fn.assert_called_once()
        call_args = create_fn.call_args[0]
        assert len(call_args) == 1
        assert call_args[0].config is yaml_config

    def test_forces_strict_gold_validation_in_prod(self) -> None:
        """Prod runs should always force strict Gold validation."""
        yaml_config = MagicMock()
        create_fn = MagicMock(return_value=MagicMock())
        assemble_fn = MagicMock(return_value=MagicMock())
        settings = SimpleNamespace(env="prod", test_mode=False)
        runtime = SimpleNamespace(strict_gold_validation=False)

        create_factory_runner(
            request=_CreateFactoryRunnerRequest(
                pipeline_name="test",
                silver_schema=None,
                gold_schema=MagicMock(),
                run_id="r1",
                runtime=runtime,
                settings=settings,
                observability=MagicMock(
                    logger=MagicMock(),
                    tracer=MagicMock(),
                    metrics=MagicMock(),
                    dq_monitor=None,
                ),
                config=yaml_config,
            ),
            create_with_services_fn=create_fn,
            assemble_runner_fn=assemble_fn,
        )

        assert assemble_fn.call_args.kwargs["strict_gold_validation"] is True
