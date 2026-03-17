"""Unit tests for GenericPipelineFactory assembler."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.pipeline.assembler import (
    GenericPipelineFactory,
    _extract_entity_type,
    assemble_runner,
    create_pipeline_factory,
)


@pytest.mark.unit
class TestExtractEntityType:
    """Tests for _extract_entity_type helper."""

    def test_extracts_suffix_after_underscore(self) -> None:
        assert _extract_entity_type("chembl_activity") == "activity"

    def test_returns_none_when_no_underscore(self) -> None:
        assert _extract_entity_type("chembl") is None

    def test_handles_multiple_underscores(self) -> None:
        assert _extract_entity_type("chembl_compound_record") == "record"


@pytest.mark.unit
class TestGenericPipelineFactory:
    """Tests for GenericPipelineFactory construction."""

    def test_raises_without_gold_schema(self) -> None:
        """gold_schema is required; raises ValueError when None."""
        with pytest.raises(ValueError, match="gold_schema is required"):
            GenericPipelineFactory(
                pipeline_name="chembl_activity",
                pipeline_class=MagicMock(),
                provider="chembl",
                gold_schema=None,
            )

    def test_stores_attributes(self) -> None:
        """Factory stores all constructor arguments as attributes."""
        gold_schema = MagicMock()
        factory = GenericPipelineFactory(
            pipeline_name="chembl_activity",
            pipeline_class=MagicMock,
            provider="chembl",
            gold_schema=gold_schema,
            silver_schema=MagicMock(),
        )

        assert factory.pipeline_name == "chembl_activity"
        assert factory.provider == "chembl"
        assert factory.gold_schema is gold_schema

    @patch("bioetl.composition.factories.pipeline.assembler.get_data_source_creator")
    def test_resolves_default_data_source_creator(
        self, mock_get_creator: MagicMock
    ) -> None:
        """When no data_source_creator provided, resolves via provider name."""
        mock_creator = MagicMock()
        mock_get_creator.return_value = mock_creator

        factory = GenericPipelineFactory(
            pipeline_name="chembl_activity",
            pipeline_class=MagicMock,
            provider="chembl",
            gold_schema=MagicMock(),
        )

        assert factory._create_data_source is mock_creator
        mock_get_creator.assert_called_once_with("chembl")

    def test_uses_custom_data_source_creator(self) -> None:
        """Explicit data_source_creator is used instead of resolved one."""
        custom_creator = MagicMock()
        factory = GenericPipelineFactory(
            pipeline_name="chembl_activity",
            pipeline_class=MagicMock,
            provider="chembl",
            gold_schema=MagicMock(),
            data_source_creator=custom_creator,
        )

        assert factory._create_data_source is custom_creator

    def test_create_transformer_delegates(self) -> None:
        """create_transformer delegates to create_transformer_instance helper."""
        factory = GenericPipelineFactory(
            pipeline_name="chembl_activity",
            pipeline_class=MagicMock,
            provider="chembl",
            gold_schema=MagicMock(),
            data_source_creator=MagicMock(),
            transformer_class=None,
        )

        result = factory.create_transformer()
        assert result is None


@pytest.mark.unit
class TestCreatePipelineFactory:
    """Tests for create_pipeline_factory convenience function."""

    @patch("bioetl.composition.factories.pipeline.assembler.get_data_source_creator")
    def test_returns_generic_pipeline_factory(
        self, mock_get_creator: MagicMock
    ) -> None:
        """create_pipeline_factory returns a GenericPipelineFactory instance."""
        mock_get_creator.return_value = MagicMock()
        factory = create_pipeline_factory(
            pipeline_name="test_pipeline",
            pipeline_class=MagicMock,
            provider="test",
            gold_schema=MagicMock(),
        )

        assert isinstance(factory, GenericPipelineFactory)
        assert factory.pipeline_name == "test_pipeline"


@pytest.mark.unit
class TestAssembleRunner:
    """Tests for assemble_runner top-level function."""

    @patch("bioetl.composition.factories.pipeline.assembler._assemble_runner_impl")
    @patch("bioetl.composition.factories.pipeline.assembler._extract_dq_configs")
    def test_delegates_to_impl(self, mock_dq: MagicMock, mock_impl: MagicMock) -> None:
        """assemble_runner delegates to _assemble_runner_impl with dq extractor."""
        expected_runner = MagicMock()
        mock_impl.return_value = expected_runner

        pipeline = MagicMock()
        obs = MagicMock()
        gold = MagicMock()

        result = assemble_runner(
            pipeline=pipeline,
            observability=obs,
            silver_schema=None,
            gold_schema=gold,
            strict_gold_validation=True,
        )

        assert result is expected_runner
        mock_impl.assert_called_once()
        call_kwargs = mock_impl.call_args[1]
        assert call_kwargs["pipeline"] is pipeline
        assert call_kwargs["dq_configs_extractor"] is mock_dq
