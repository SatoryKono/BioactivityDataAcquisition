"""Unit tests for _creation_wiring pipeline creation internals."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.domain.config import DQConfig
from bioetl.composition.factories.pipeline._creation_wiring import (
    _PipelineCreationInputs,
    _PipelineCreationRequest,
    _create_pipeline_with_services_impl,
    _create_silver_validator,
)

_STARTED_AT = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)


@pytest.mark.unit
class TestPipelineCreationInputs:
    """Tests for _PipelineCreationInputs dataclass."""

    def test_is_frozen_dataclass(self) -> None:
        """Dataclass is frozen and slots-based."""
        inputs = _PipelineCreationInputs(
            pipeline_name="test",
            pipeline_class=MagicMock,
            provider="chembl",
            create_data_source_fn=MagicMock(),
            transformer_class=None,
            request=_PipelineCreationRequest(
                run_id="run-1",
                runtime=SimpleNamespace(),
                started_at=_STARTED_AT,
                settings=SimpleNamespace(),
                logger=MagicMock(),
                audit=MagicMock(),
            ),
        )

        assert inputs.pipeline_name == "test"
        assert inputs.provider == "chembl"
        assert inputs.transformer_class is None

    def test_optional_fields_default_none(self) -> None:
        """Optional fields default to None."""
        inputs = _PipelineCreationInputs(
            pipeline_name="p",
            pipeline_class=MagicMock,
            provider="pr",
            create_data_source_fn=MagicMock(),
            transformer_class=None,
            request=_PipelineCreationRequest(
                run_id="r",
                runtime=SimpleNamespace(),
                started_at=_STARTED_AT,
                settings=SimpleNamespace(),
                logger=MagicMock(),
                audit=MagicMock(),
            ),
        )

        assert inputs.request.config is None
        assert inputs.request.filter_config is None
        assert inputs.request.tracer is None
        assert inputs.request.dq_monitor is None
        assert inputs.request.metrics is None
        assert inputs.request.cached_bronze is None
        assert inputs.pandera_silver_schema is None


@pytest.mark.unit
class TestCreateSilverValidator:
    """Tests for _create_silver_validator."""

    def test_returns_none_when_no_schema(self) -> None:
        """Returns None when pandera_silver_schema is None."""
        result = _create_silver_validator(None)
        assert result is None

    @patch("bioetl.infrastructure.validation.ContractAwareSilverValidator")
    def test_creates_validator_with_schema(self, mock_validator_cls: MagicMock) -> None:
        """Creates ContractAwareSilverValidator when schema is provided."""
        schema = MagicMock()
        schema.to_schema.return_value = MagicMock()
        expected = MagicMock()
        mock_validator_cls.return_value = expected
        dq_config = DQConfig(contract_ref="chembl_activity")

        result = _create_silver_validator(schema, dq_config)

        assert result is expected
        mock_validator_cls.assert_called_once_with(
            schema.to_schema.return_value,
            dq_config=dq_config,
        )


@pytest.mark.unit
class TestCreatePipelineWithServicesImpl:
    """Tests for _create_pipeline_with_services_impl."""

    @patch(
        "bioetl.composition.factories.pipeline._creation_wiring._create_silver_validator"
    )
    @patch("bioetl.composition.factories.pipeline._creation_wiring.TransformerBuilder")
    @patch(
        "bioetl.composition.factories.pipeline._creation_wiring.resolve_domain_pipeline_config"
    )
    @patch("bioetl.composition.factories.pipeline._creation_wiring.RunContextFactory")
    @patch("bioetl.composition.factories.pipeline._creation_wiring.MetadataCoordinator")
    def test_creates_pipeline(
        self,
        mock_meta_coord: MagicMock,
        mock_run_ctx_factory: MagicMock,
        mock_resolve_domain_pipeline_config: MagicMock,
        mock_transformer_builder: MagicMock,
        mock_silver_validator: MagicMock,
    ) -> None:
        """_create_pipeline_with_services_impl wires all components and returns pipeline."""
        from bioetl.composition.factories.pipeline._creation_wiring import (
            _create_pipeline_with_services_impl,
        )

        mock_silver_validator.return_value = None

        # Setup run context factory chain
        run_ctx_instance = MagicMock()
        run_ctx_instance.create.return_value = MagicMock()
        mock_run_ctx_factory.return_value = run_ctx_instance

        mock_resolve_domain_pipeline_config.return_value = MagicMock()

        # Setup transformer builder chain
        builder_instance = MagicMock()
        builder_instance.build.return_value = MagicMock()
        mock_transformer_builder.return_value = builder_instance

        # Pipeline class
        pipeline_cls = MagicMock()
        expected_pipeline = MagicMock()
        pipeline_cls.create.return_value = expected_pipeline

        deps = MagicMock()
        deps.load_pipeline_config.return_value = MagicMock()

        settings = SimpleNamespace(pipeline=SimpleNamespace(relaxed_dq=False))
        inputs = _PipelineCreationInputs(
            pipeline_name="test",
            pipeline_class=pipeline_cls,
            provider="chembl",
            create_data_source_fn=MagicMock(),
            transformer_class=None,
            request=_PipelineCreationRequest(
                run_id="run-1",
                runtime=MagicMock(),
                started_at=_STARTED_AT,
                settings=settings,
                logger=MagicMock(),
                audit=MagicMock(),
            ),
        )

        build_services_fn = MagicMock(return_value=MagicMock())

        result = _create_pipeline_with_services_impl(
            inputs,
            deps=deps,
            extract_entity_type=lambda n: n.split("_")[-1] if "_" in n else None,
            build_pipeline_services_fn=build_services_fn,
        )

        assert result is expected_pipeline
        pipeline_cls.create.assert_called_once()

    @patch(
        "bioetl.composition.factories.pipeline._creation_wiring._create_silver_validator"
    )
    @patch("bioetl.composition.factories.pipeline._creation_wiring.TransformerBuilder")
    @patch(
        "bioetl.composition.factories.pipeline._creation_wiring.resolve_domain_pipeline_config"
    )
    @patch("bioetl.composition.factories.pipeline._creation_wiring.RunContextFactory")
    @patch("bioetl.composition.factories.pipeline._creation_wiring.MetadataCoordinator")
    def test_uses_explicit_config_and_forwards_optional_dependencies(
        self,
        mock_metadata_coordinator: MagicMock,
        mock_run_context_factory: MagicMock,
        mock_resolve_domain_pipeline_config: MagicMock,
        mock_transformer_builder: MagicMock,
        mock_create_silver_validator: MagicMock,
    ) -> None:
        """Explicit config path should avoid fallback loading and preserve wiring."""
        run_context = MagicMock()
        metadata_coordinator = MagicMock()
        services = MagicMock()
        domain_config = MagicMock()
        transformer = MagicMock()
        silver_validator = MagicMock()
        explicit_config = MagicMock()
        cached_bronze = MagicMock()
        tracer = MagicMock()
        dq_monitor = MagicMock()
        metrics = MagicMock()
        filter_config = MagicMock()
        runtime = MagicMock()
        logger = MagicMock()

        mock_run_context_factory.return_value.create.return_value = run_context
        mock_metadata_coordinator.return_value = metadata_coordinator
        mock_resolve_domain_pipeline_config.return_value = domain_config
        mock_create_silver_validator.return_value = silver_validator
        mock_transformer_builder.return_value.build.return_value = transformer

        pipeline_cls = MagicMock()
        expected_pipeline = MagicMock()
        pipeline_cls.create.return_value = expected_pipeline

        deps = MagicMock()
        settings = SimpleNamespace(pipeline=SimpleNamespace(relaxed_dq=True))
        inputs = _PipelineCreationInputs(
            pipeline_name="chembl_activity",
            pipeline_class=pipeline_cls,
            provider="chembl",
            create_data_source_fn=MagicMock(),
            transformer_class=MagicMock(),
            request=_PipelineCreationRequest(
                run_id="run-42",
                runtime=runtime,
                started_at=_STARTED_AT,
                settings=settings,
                logger=logger,
                config=explicit_config,
                filter_config=filter_config,
                tracer=tracer,
                dq_monitor=dq_monitor,
                metrics=metrics,
                cached_bronze=cached_bronze,
                audit=MagicMock(),
            ),
            pandera_silver_schema=MagicMock(),
        )
        build_services_fn = MagicMock(return_value=services)

        result = _create_pipeline_with_services_impl(
            inputs,
            deps=deps,
            extract_entity_type=lambda n: n.split("_")[-1] if "_" in n else None,
            build_pipeline_services_fn=build_services_fn,
        )

        assert result is expected_pipeline
        deps.load_pipeline_config.assert_not_called()
        build_services_fn.assert_called_once_with(
            pipeline_name="chembl_activity",
            create_data_source_fn=inputs.create_data_source_fn,
            settings=settings,
            logger=logger,
            audit=inputs.request.audit,
            config=explicit_config,
            filter_config=filter_config,
            tracer=tracer,
            dq_monitor=dq_monitor,
            metadata_coordinator=metadata_coordinator,
            cached_bronze=cached_bronze,
            silver_validator=silver_validator,
        )
        mock_resolve_domain_pipeline_config.assert_called_once_with(
            explicit_config,
            relaxed_dq=True,
            domain_mapper=deps.yaml_config_to_domain,
        )
        pipeline_cls.create.assert_called_once()
        create_kwargs = pipeline_cls.create.call_args.kwargs
        assert create_kwargs["services"] is services
        assert create_kwargs["config"] is domain_config
        assert create_kwargs["started_at"] == _STARTED_AT
        assert create_kwargs["transformer"] is transformer

    @patch(
        "bioetl.composition.factories.pipeline._creation_wiring._create_silver_validator"
    )
    @patch("bioetl.composition.factories.pipeline._creation_wiring.TransformerBuilder")
    @patch(
        "bioetl.composition.factories.pipeline._creation_wiring.resolve_domain_pipeline_config"
    )
    @patch("bioetl.composition.factories.pipeline._creation_wiring.RunContextFactory")
    @patch("bioetl.composition.factories.pipeline._creation_wiring.MetadataCoordinator")
    def test_loads_config_when_inputs_config_missing(
        self,
        mock_metadata_coordinator: MagicMock,
        mock_run_context_factory: MagicMock,
        mock_resolve_domain_pipeline_config: MagicMock,
        mock_transformer_builder: MagicMock,
        mock_create_silver_validator: MagicMock,
    ) -> None:
        """Missing config should trigger loader and thread loaded config onward."""
        loaded_config = MagicMock()
        services = MagicMock()
        domain_config = MagicMock()
        transformer = MagicMock()
        metadata_coordinator = MagicMock()

        deps = MagicMock()
        deps.load_pipeline_config.return_value = loaded_config
        settings = SimpleNamespace(pipeline=SimpleNamespace(relaxed_dq=False))
        pipeline_cls = MagicMock()
        pipeline_cls.create.return_value = MagicMock()

        mock_run_context_factory.return_value.create.return_value = MagicMock()
        mock_metadata_coordinator.return_value = metadata_coordinator
        mock_resolve_domain_pipeline_config.return_value = domain_config
        mock_create_silver_validator.return_value = None
        mock_transformer_builder.return_value.build.return_value = transformer

        inputs = _PipelineCreationInputs(
            pipeline_name="chembl_activity",
            pipeline_class=pipeline_cls,
            provider="chembl",
            create_data_source_fn=MagicMock(),
            transformer_class=None,
            request=_PipelineCreationRequest(
                run_id="run-7",
                runtime=MagicMock(),
                started_at=_STARTED_AT,
                settings=settings,
                logger=MagicMock(),
                audit=MagicMock(),
            ),
        )
        build_services_fn = MagicMock(return_value=services)

        _create_pipeline_with_services_impl(
            inputs,
            deps=deps,
            extract_entity_type=lambda n: n.split("_")[-1] if "_" in n else None,
            build_pipeline_services_fn=build_services_fn,
        )

        deps.load_pipeline_config.assert_called_once_with("chembl_activity")
        build_services_fn.assert_called_once()
        assert build_services_fn.call_args.kwargs["config"] is loaded_config
        mock_resolve_domain_pipeline_config.assert_called_once_with(
            loaded_config,
            relaxed_dq=False,
            domain_mapper=deps.yaml_config_to_domain,
        )
