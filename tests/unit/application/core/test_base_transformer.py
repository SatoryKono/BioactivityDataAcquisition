"""Unit tests for BaseTransformer helper methods.

Tests the new Template Method pattern and helper methods:
- _get_required_field()
- _extract_nested()
- _create_entity()
- _safe_get()
- TransformationError handling
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.base_transformer import (
    BaseTransformer,
    TransformationError,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.entities import Activity
from bioetl.domain.types import RunType


class ConcreteTransformer(BaseTransformer):
    """Concrete implementation for testing."""

    async def _transform_impl(self, context, record):
        """Simple implementation that uses helper methods."""
        pk = self._get_required_field(record, "id")
        return {"id": pk, "value": record.get("value")}


@pytest.fixture
def mock_context() -> PipelineContext:
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


@pytest.fixture
def transformer() -> ConcreteTransformer:
    """Create a concrete transformer for testing."""
    return ConcreteTransformer(provider="test")


@pytest.mark.unit
class TestTransformationError:
    """Tests for TransformationError exception."""

    def test_error_with_field(self) -> None:
        """Test TransformationError stores field name."""
        error = TransformationError("Missing field: test", field="test")
        assert str(error) == "Missing field: test"
        assert error.field == "test"

    def test_error_without_field(self) -> None:
        """Test TransformationError works without field."""
        error = TransformationError("Generic error")
        assert str(error) == "Generic error"
        assert error.field is None


@pytest.mark.unit
class TestGetRequiredField:
    """Tests for _get_required_field helper method."""

    def test_returns_value_when_present(self, transformer: ConcreteTransformer) -> None:
        """Test returns field value when present."""
        record = {"field": "value"}
        result = transformer._get_required_field(record, "field")
        assert result == "value"

    def test_raises_when_missing(self, transformer: ConcreteTransformer) -> None:
        """Test raises TransformationError when field is missing."""
        record = {"other": "value"}
        with pytest.raises(TransformationError) as exc_info:
            transformer._get_required_field(record, "field")
        assert "Missing required field: field" in str(exc_info.value)
        assert exc_info.value.field == "field"

    def test_raises_when_none(self, transformer: ConcreteTransformer) -> None:
        """Test raises TransformationError when field is None."""
        record = {"field": None}
        with pytest.raises(TransformationError) as exc_info:
            transformer._get_required_field(record, "field")
        assert "Missing required field" in str(exc_info.value)

    def test_raises_when_empty_string(self, transformer: ConcreteTransformer) -> None:
        """Test raises TransformationError when field is empty string."""
        record = {"field": "   "}
        with pytest.raises(TransformationError) as exc_info:
            transformer._get_required_field(record, "field")
        assert "Required field is empty" in str(exc_info.value)

    def test_allows_empty_when_specified(
        self, transformer: ConcreteTransformer
    ) -> None:
        """Test allows empty values when allow_empty=True."""
        record = {"field": ""}
        result = transformer._get_required_field(record, "field", allow_empty=True)
        assert result == ""

    def test_raises_when_empty_list(self, transformer: ConcreteTransformer) -> None:
        """Test raises TransformationError when field is empty list."""
        record = {"field": []}
        with pytest.raises(TransformationError) as exc_info:
            transformer._get_required_field(record, "field")
        assert "Required field is empty" in str(exc_info.value)

    def test_raises_when_empty_dict(self, transformer: ConcreteTransformer) -> None:
        """Test raises TransformationError when field is empty dict."""
        record = {"field": {}}
        with pytest.raises(TransformationError) as exc_info:
            transformer._get_required_field(record, "field")
        assert "Required field is empty" in str(exc_info.value)

    def test_allows_zero_value(self, transformer: ConcreteTransformer) -> None:
        """Test allows zero as valid value."""
        record = {"field": 0}
        result = transformer._get_required_field(record, "field")
        assert result == 0


@pytest.mark.unit
class TestExtractNested:
    """Tests for _extract_nested helper method."""

    def test_extracts_single_level(self, transformer: ConcreteTransformer) -> None:
        """Test extracts single level field."""
        record = {"field": "value"}
        result = transformer._extract_nested(record, "field")
        assert result == "value"

    def test_extracts_nested_field(self, transformer: ConcreteTransformer) -> None:
        """Test extracts nested field with dot notation."""
        record = {"level1": {"level2": {"level3": "value"}}}
        result = transformer._extract_nested(record, "level1.level2.level3")
        assert result == "value"

    def test_returns_default_when_path_missing(
        self, transformer: ConcreteTransformer
    ) -> None:
        """Test returns default when path doesn't exist."""
        record = {"other": "value"}
        result = transformer._extract_nested(record, "missing.path", default="default")
        assert result == "default"

    def test_returns_default_when_intermediate_none(
        self, transformer: ConcreteTransformer
    ) -> None:
        """Test returns default when intermediate value is None."""
        record = {"level1": None}
        result = transformer._extract_nested(record, "level1.level2", default="default")
        assert result == "default"

    def test_returns_default_when_intermediate_not_dict(
        self, transformer: ConcreteTransformer
    ) -> None:
        """Test returns default when intermediate value is not dict."""
        record = {"level1": "not_a_dict"}
        result = transformer._extract_nested(record, "level1.level2", default="default")
        assert result == "default"

    def test_returns_none_as_default(self, transformer: ConcreteTransformer) -> None:
        """Test returns None as default if not specified."""
        record = {"other": "value"}
        result = transformer._extract_nested(record, "missing")
        assert result is None

    def test_extracts_numeric_value(self, transformer: ConcreteTransformer) -> None:
        """Test extracts numeric value from nested path."""
        record = {"organism": {"taxonId": 9606}}
        result = transformer._extract_nested(record, "organism.taxonId")
        assert result == 9606


@pytest.mark.unit
class TestSafeGet:
    """Tests for _safe_get helper method."""

    def test_returns_value_when_present(self, transformer: ConcreteTransformer) -> None:
        """Test returns field value when present."""
        record = {"field": "value"}
        result = transformer._safe_get(record, "field")
        assert result == "value"

    def test_returns_default_when_missing(
        self, transformer: ConcreteTransformer
    ) -> None:
        """Test returns default when field is missing."""
        record = {"other": "value"}
        result = transformer._safe_get(record, "field", default="default")
        assert result == "default"

    def test_returns_default_when_none(self, transformer: ConcreteTransformer) -> None:
        """Test returns default when field is None."""
        record = {"field": None}
        result = transformer._safe_get(record, "field", default="default")
        assert result == "default"

    def test_returns_none_as_default(self, transformer: ConcreteTransformer) -> None:
        """Test returns None as default if not specified."""
        record = {"other": "value"}
        result = transformer._safe_get(record, "field")
        assert result is None


@pytest.mark.unit
class TestCreateEntity:
    """Tests for _create_entity helper method."""

    def test_creates_entity_with_lineage(
        self, transformer: ConcreteTransformer, mock_context: PipelineContext
    ) -> None:
        """Test creates entity with lineage fields from context."""
        entity = transformer._create_entity(
            Activity,
            mock_context,
            entity_id="test:activity:123",
            content_hash="abc123",
            activity_id="123",
            molecule_chembl_id="CHEMBL25",
        )

        assert entity.entity_id == "test:activity:123"
        assert entity.content_hash == "abc123"
        assert entity.run_id == mock_context.run_id
        assert entity.run_type == mock_context.run_type
        assert entity.source_batch_id is None
        assert entity.activity_id == "123"
        assert entity.molecule_chembl_id == "CHEMBL25"

    def test_raises_on_invalid_entity_data(
        self, transformer: ConcreteTransformer, mock_context: PipelineContext
    ) -> None:
        """Test raises ValueError when entity validation fails."""
        with pytest.raises(ValueError):
            transformer._create_entity(
                Activity,
                mock_context,
                entity_id="test:activity:123",
                content_hash="abc123",
                activity_id="",  # Invalid: empty activity_id
                molecule_chembl_id="CHEMBL25",
            )


@pytest.mark.unit
class TestTemplateMethodPattern:
    """Tests for Template Method pattern in transform()."""

    @pytest.mark.asyncio
    async def test_transform_calls_transform_impl(
        self, transformer: ConcreteTransformer, mock_context: PipelineContext
    ) -> None:
        """Test transform() delegates to _transform_impl()."""
        record = {"id": "123", "value": "test"}
        result = await transformer.transform(mock_context, record)
        assert result == {"id": "123", "value": "test"}

    @pytest.mark.asyncio
    async def test_transform_handles_transformation_error(
        self, transformer: ConcreteTransformer, mock_context: PipelineContext
    ) -> None:
        """Test transform() handles TransformationError and returns None."""
        record = {"value": "test"}  # Missing required 'id' field
        result = await transformer.transform(mock_context, record)

        assert result is None
        mock_context.logger.warning.assert_called_once()
        call_args = mock_context.logger.warning.call_args
        assert "transformation_skipped" in call_args[0]

    @pytest.mark.asyncio
    async def test_transform_handles_value_error(
        self, mock_context: PipelineContext
    ) -> None:
        """Test transform() handles ValueError and returns None."""

        class FailingTransformer(BaseTransformer):
            async def _transform_impl(self, context, record):
                raise ValueError("Entity validation failed")

        transformer = FailingTransformer(provider="test")
        result = await transformer.transform(mock_context, {"id": "123"})

        assert result is None
        mock_context.logger.warning.assert_called_once()
        call_args = mock_context.logger.warning.call_args
        assert "entity_validation_failed" in call_args[0]
