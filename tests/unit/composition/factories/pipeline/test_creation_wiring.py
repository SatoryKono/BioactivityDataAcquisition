"""Unit tests for _creation_wiring pipeline creation internals."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.pipeline._creation_wiring import (
    _PipelineCreationInputs,
    _create_silver_validator,
)


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
            run_id="run-1",
            runtime=SimpleNamespace(),
            settings=SimpleNamespace(),
            logger=MagicMock(),
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
            run_id="r",
            runtime=SimpleNamespace(),
            settings=SimpleNamespace(),
            logger=MagicMock(),
        )

        assert inputs.config is None
        assert inputs.filter_config is None
        assert inputs.tracer is None
        assert inputs.dq_monitor is None
        assert inputs.metrics is None
        assert inputs.cached_bronze is None
        assert inputs.pandera_silver_schema is None


@pytest.mark.unit
class TestCreateSilverValidator:
    """Tests for _create_silver_validator."""

    def test_returns_none_when_no_schema(self) -> None:
        """Returns None when pandera_silver_schema is None."""
        result = _create_silver_validator(None)
        assert result is None

    @patch("bioetl.infrastructure.validation.pandera_validator.PanderaSilverValidator")
    def test_creates_validator_with_schema(self, mock_validator_cls: MagicMock) -> None:
        """Creates PanderaSilverValidator when schema is provided."""
        schema = MagicMock()
        schema.to_schema.return_value = MagicMock()
        expected = MagicMock()
        mock_validator_cls.return_value = expected

        result = _create_silver_validator(schema)

        assert result is expected
        mock_validator_cls.assert_called_once()


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
            run_id="run-1",
            runtime=MagicMock(),
            settings=settings,
            logger=MagicMock(),
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
