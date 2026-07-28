"""Unit tests for pipeline contract_validator."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition.factories.pipeline.contract_validator import (
    _resolve_transformer_class_ref,
    _resolve_silver_columns,
    _schema_columns,
    _validate_contract_policy,
    create_factory,
)
from bioetl.composition.providers.provider_registry import create_provider_registry


@pytest.mark.unit
class TestResolveTransformerClassRef:
    """Tests for manifest transformer reference resolution."""

    def test_returns_none_for_none(self) -> None:
        assert _resolve_transformer_class_ref(None) is None

    def test_returns_existing_class_as_is(self) -> None:
        class _Transformer:
            pass

        assert _resolve_transformer_class_ref(_Transformer) is _Transformer

    def test_resolves_import_path_string(self) -> None:
        resolved = _resolve_transformer_class_ref(
            "bioetl.application.pipelines.pubchem.transformer.PubChemCompoundTransformer"
        )

        assert resolved is not None
        assert resolved.__name__ == "PubChemCompoundTransformer"


@pytest.mark.unit
class TestSchemaColumns:
    """Tests for _schema_columns helper."""

    def test_extracts_column_names(self) -> None:
        """Extracts column names from a schema with to_schema()."""
        schema_cls = MagicMock()
        resolved = MagicMock()
        resolved.columns = {"col_a": MagicMock(), "col_b": MagicMock()}
        schema_cls.to_schema.return_value = resolved

        result = _schema_columns(schema_cls)

        assert result == {"col_a", "col_b"}

    def test_raises_when_no_to_schema(self) -> None:
        """Raises ValueError when schema has no to_schema method."""
        schema_cls = SimpleNamespace()  # no to_schema

        with pytest.raises(ValueError, match="does not expose to_schema"):
            _schema_columns(schema_cls)


@pytest.mark.unit
class TestResolveSilverColumns:
    """Tests for _resolve_silver_columns."""

    def test_uses_pandera_silver_schema_first(self) -> None:
        """Prefers pandera_silver_schema when available."""
        pandera_schema = MagicMock()
        resolved = MagicMock()
        resolved.columns = {"x": MagicMock()}
        pandera_schema.to_schema.return_value = resolved

        config = SimpleNamespace(
            pandera_silver_schema=pandera_schema,
            silver_schema=MagicMock(),
            provider="test",
            entity_type="entity",
        )

        result = _resolve_silver_columns(config)
        assert "x" in result

    def test_falls_back_to_arrow_silver_schema(self) -> None:
        """Uses silver_schema.names when pandera_silver_schema is None."""
        arrow_schema = MagicMock()
        arrow_schema.names = ["a", "b"]

        config = SimpleNamespace(
            pandera_silver_schema=None,
            silver_schema=arrow_schema,
            provider="test",
            entity_type="entity",
        )

        result = _resolve_silver_columns(config)
        assert result == {"a", "b"}

    def test_raises_when_no_schema_available(self) -> None:
        """Raises ValueError when neither schema source is available."""
        config = SimpleNamespace(
            pandera_silver_schema=None,
            silver_schema=None,
            provider="test",
            entity_type="entity",
        )

        with pytest.raises(ValueError, match="No Silver schema"):
            _resolve_silver_columns(config)


@pytest.mark.unit
class TestValidateContractPolicy:
    """Tests for _validate_contract_policy."""

    @patch(
        "bioetl.composition.factories.pipeline_support.contract_validation_helpers.load_pipeline_contract_policy"
    )
    def test_passes_when_keys_present(self, mock_load_policy: MagicMock) -> None:
        """No error when all policy keys exist in both schemas."""
        mock_load_policy.return_value = SimpleNamespace(
            primary_key=["pk"], merge_keys=["mk"]
        )

        pandera_schema = MagicMock()
        resolved = MagicMock()
        resolved.columns = {"pk": MagicMock(), "mk": MagicMock(), "extra": MagicMock()}
        pandera_schema.to_schema.return_value = resolved

        gold_schema = MagicMock()
        gold_resolved = MagicMock()
        gold_resolved.columns = {"pk": MagicMock(), "mk": MagicMock()}
        gold_schema.to_schema.return_value = gold_resolved

        config = SimpleNamespace(
            provider="test",
            entity_type="entity",
            pandera_silver_schema=pandera_schema,
            silver_schema=None,
            gold_schema=gold_schema,
        )

        # Should not raise
        _validate_contract_policy(config)

        mock_load_policy.assert_called_once_with("test", "entity")

    @patch(
        "bioetl.composition.factories.pipeline_support.contract_validation_helpers.load_pipeline_contract_policy"
    )
    def test_raises_when_keys_missing(self, mock_load_policy: MagicMock) -> None:
        """Raises ValueError when policy keys are missing from schemas."""
        mock_load_policy.return_value = SimpleNamespace(
            primary_key=["pk", "missing_key"], merge_keys=[]
        )

        pandera_schema = MagicMock()
        resolved = MagicMock()
        resolved.columns = {"pk": MagicMock()}
        pandera_schema.to_schema.return_value = resolved

        gold_schema = MagicMock()
        gold_resolved = MagicMock()
        gold_resolved.columns = {"pk": MagicMock()}
        gold_schema.to_schema.return_value = gold_resolved

        config = SimpleNamespace(
            provider="test",
            entity_type="entity",
            pandera_silver_schema=pandera_schema,
            silver_schema=None,
            gold_schema=gold_schema,
        )

        with pytest.raises(ValueError, match="Invalid contract policy"):
            _validate_contract_policy(config)


@pytest.mark.unit
class TestCreateFactory:
    """Tests for create_factory."""

    @patch(
        "bioetl.composition.factories.pipeline._assembler_factory.get_data_source_creator"
    )
    @patch(
        "bioetl.composition.factories.pipeline.contract_validator._validate_contract_policy"
    )
    def test_create_factory__pipeline_factory__829bdf23(
        self,
        mock_validate: MagicMock,
        mock_get_creator: MagicMock,
    ) -> None:
        """create_factory returns a GenericPipelineFactory."""
        mock_get_creator.return_value = MagicMock()
        config = SimpleNamespace(
            pipeline_name="test_pipe",
            provider="test",
            entity_type="entity",
            silver_schema=None,
            gold_schema=MagicMock(),
            pandera_silver_schema=None,
            transformer_class=None,
            data_source_provider=None,
        )

        result = create_factory(config)

        assert result is not None
        assert result.pipeline_name == "test_pipe"

    @patch(
        "bioetl.composition.factories.pipeline._assembler_factory.get_data_source_creator"
    )
    @patch(
        "bioetl.composition.factories.pipeline.contract_validator._validate_contract_policy"
    )
    def test_create_factory_resolves_string_transformer_reference(
        self,
        mock_validate: MagicMock,
        mock_get_creator: MagicMock,
    ) -> None:
        mock_get_creator.return_value = MagicMock()
        config = SimpleNamespace(
            pipeline_name="pubchem_compound",
            provider="pubchem",
            entity_type="compound",
            silver_schema=None,
            gold_schema=MagicMock(),
            pandera_silver_schema=None,
            transformer_class="bioetl.application.pipelines.pubchem.transformer.PubChemCompoundTransformer",
            data_source_provider=None,
        )

        result = create_factory(config)

        assert result.transformer_class is not None
        assert result.transformer_class.__name__ == "PubChemCompoundTransformer"

    @patch(
        "bioetl.composition.factories.pipeline._assembler_factory.get_data_source_creator"
    )
    @patch(
        "bioetl.composition.factories.pipeline.contract_validator._validate_contract_policy"
    )
    @patch(
        "bioetl.composition.factories.pipeline.contract_validator.get_data_source_creator"
    )
    def test_uses_data_source_provider_override(
        self,
        mock_get_creator_cv: MagicMock,
        mock_validate: MagicMock,
        mock_get_creator_asm: MagicMock,
    ) -> None:
        """When data_source_provider is set, it resolves a custom creator."""
        mock_get_creator_cv.return_value = MagicMock()
        mock_get_creator_asm.return_value = MagicMock()
        config = SimpleNamespace(
            pipeline_name="test_pipe",
            provider="test",
            entity_type="entity",
            silver_schema=None,
            gold_schema=MagicMock(),
            pandera_silver_schema=None,
            transformer_class=None,
            data_source_provider="custom_provider",
        )

        create_factory(config)

        mock_get_creator_cv.assert_called_once_with(
            "custom_provider",
            provider_registry=None,
        )

    @patch(
        "bioetl.composition.factories.pipeline._assembler_factory.get_data_source_creator"
    )
    @patch(
        "bioetl.composition.factories.pipeline.contract_validator._validate_contract_policy"
    )
    @patch(
        "bioetl.composition.factories.pipeline.contract_validator.get_data_source_creator"
    )
    def test_threads_explicit_provider_registry_to_data_source_creator(
        self,
        mock_get_creator_cv: MagicMock,
        mock_validate: MagicMock,
        mock_get_creator_asm: MagicMock,
    ) -> None:
        """create_factory should pass explicit provider registry to creator resolution."""
        mock_get_creator_cv.return_value = MagicMock()
        mock_get_creator_asm.return_value = MagicMock()
        registry = create_provider_registry()
        config = SimpleNamespace(
            pipeline_name="test_pipe",
            provider="test",
            entity_type="entity",
            silver_schema=None,
            gold_schema=MagicMock(),
            pandera_silver_schema=None,
            transformer_class=None,
            data_source_provider="custom_provider",
        )

        result = create_factory(config, provider_registry=registry)

        assert result.provider_registry is registry
        mock_get_creator_cv.assert_called_once_with(
            "custom_provider",
            provider_registry=registry,
        )
