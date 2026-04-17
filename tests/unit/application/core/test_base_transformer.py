"""Unit tests for BaseTransformer helper methods.

Tests the new Template Method pattern and helper methods:
- _get_required_field()
- _extract_nested()
- _create_entity()
- _safe_get()
- TransformationError handling
- should_write_gold() (New)
- transform_for_gold() (New)
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.core.base_transformer import (
    BaseTransformer,
    FilteredOutError,
    TransformationError,
)
from bioetl.application.core.base_transformer.structural_policy import (
    StructuralPolicyEvent,
    StructuralPolicyOutcome,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.entities import Bioactivity
from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
from bioetl.domain.types import BatchID, RunType
from tests.helpers.transformer_dependencies import (
    build_test_transformer_dependencies,
)


class ConcreteTransformer(BaseTransformer):
    """Concrete implementation for testing."""

    async def _transform_impl(self, context, record, index):
        """Simple implementation that uses helper methods."""
        pk = self._get_required_field(record, "id")
        return {"id": pk, "value": record.get("value")}


class _FakeStructuralPolicy:
    def __init__(self, outcome: StructuralPolicyOutcome) -> None:
        self.outcome = outcome
        self.calls: list[dict[str, object]] = []

    def apply(self, record):
        self.calls.append(dict(record))
        return self.outcome


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
    return ConcreteTransformer(
        provider="test",
        dependencies=build_test_transformer_dependencies(),
    )


@pytest.mark.unit
def test_base_transformer_requires_explicit_dependencies() -> None:
    """BaseTransformer no longer creates collaborators implicitly."""
    with pytest.raises(TypeError, match="requires explicit collaborator injection"):
        ConcreteTransformer(provider="test")


@pytest.mark.unit
def test_base_transformer_rejects_partial_named_collaborators() -> None:
    """Named collaborator args must not trigger hidden default construction."""
    with pytest.raises(
        TypeError,
        match="no longer assembles partial collaborator defaults",
    ):
        ConcreteTransformer(
            provider="test",
            tracer=MagicMock(),
        )


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
class TestCreateEntity:
    """Tests for _create_entity helper method."""

    def test_creates_entity_with_lineage(
        self, transformer: ConcreteTransformer, mock_context: PipelineContext
    ) -> None:
        """Test creates entity with lineage fields from context."""
        entity = transformer._create_entity(
            Bioactivity,
            mock_context,
            entity_id="test:activity:123",
            content_hash="abc123",
            index=0,
            activity_id="123",
            molecule_id="CHEMBL25",
        )

        assert entity.entity_id == "test:activity:123"
        assert entity.content_hash == "abc123"
        assert entity.run_id == mock_context.run_id
        assert entity.run_type == mock_context.run_type
        assert entity.source_batch_id is None
        assert entity.activity_id == "123"
        assert entity.molecule_id == "CHEMBL25"
        assert entity._index == 0

    def test_raises_on_invalid_entity_data(
        self, transformer: ConcreteTransformer, mock_context: PipelineContext
    ) -> None:
        """Test raises ValueError when entity validation fails."""
        with pytest.raises(ValueError):
            transformer._create_entity(
                Bioactivity,
                mock_context,
                entity_id="test:activity:123",
                content_hash="abc123",
                index=0,
                activity_id="",  # Invalid: empty activity_id
                molecule_id="CHEMBL25",
            )

    def test_uses_source_batch_id_from_context(
        self, transformer: ConcreteTransformer, mock_context: PipelineContext
    ) -> None:
        """Entity lineage should inherit the active batch identifier from context."""
        batch_id = BatchID(uuid4())

        entity = transformer._create_entity(
            Bioactivity,
            mock_context.with_source_batch_id(batch_id),
            entity_id="test:activity:124",
            content_hash="def456",
            index=1,
            activity_id="124",
            molecule_id="CHEMBL26",
        )

        assert entity.source_batch_id == batch_id


@pytest.mark.unit
class TestTemplateMethodPattern:
    """Tests for Template Method pattern in transform()."""

    @pytest.mark.asyncio
    async def test_transform_calls_transform_impl(
        self, transformer: ConcreteTransformer, mock_context: PipelineContext
    ) -> None:
        """Test transform() delegates to _transform_impl() without mutating payload."""
        record = {"id": "123", "value": "test"}
        result = await transformer.transform(mock_context, record, index=0)
        assert result["id"] == "123"
        assert result["value"] == "test"
        assert "_run_id" not in result
        assert "_run_type" not in result
        assert "_source_batch_id" not in result
        assert "_ingestion_ts" not in result

    @pytest.mark.asyncio
    async def test_transform_handles_transformation_error(
        self, transformer: ConcreteTransformer, mock_context: PipelineContext
    ) -> None:
        """Test transform() handles TransformationError and returns None."""
        record = {"value": "test"}  # Missing required 'id' field
        result = await transformer.transform(mock_context, record, index=0)

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
            async def _transform_impl(self, context, record, index):
                raise ValueError("Entity validation failed")

        transformer = FailingTransformer(
            provider="test",
            dependencies=build_test_transformer_dependencies(),
        )
        result = await transformer.transform(mock_context, {"id": "123"}, index=0)

        assert result is None
        mock_context.logger.warning.assert_called_once()
        call_args = mock_context.logger.warning.call_args
        assert "entity_validation_failed" in call_args[0]

    @pytest.mark.asyncio
    async def test_transform_raises_filtered_out_error(
        self, mock_context: PipelineContext
    ) -> None:
        """Test transform() raises FilteredOutError when Silver filter excludes."""
        transformer = ConcreteTransformer(
            provider="test",
            silver_filters=SilverFilterConfig(required_fields=("must_exist",)),
            dependencies=build_test_transformer_dependencies(),
        )

        with pytest.raises(FilteredOutError):
            await transformer.transform(mock_context, {"id": "123"}, index=0)

        mock_context.logger.debug.assert_called_once()
        call_args = mock_context.logger.debug.call_args
        assert "silver_filter_quarantined" in call_args[0]

    @pytest.mark.asyncio
    async def test_transform_applies_structural_policy_before_silver_filter(
        self, mock_context: PipelineContext
    ) -> None:
        structural_policy = _FakeStructuralPolicy(
            StructuralPolicyOutcome(
                record={"id": "123", "value": "test", "must_exist": 1}
            )
        )
        transformer = ConcreteTransformer(
            provider="test",
            silver_filters=SilverFilterConfig(required_fields=("must_exist",)),
            dependencies=build_test_transformer_dependencies(
                structural_policy=structural_policy
            ),
        )

        result = await transformer.transform(
            mock_context, {"id": "123", "value": "test"}, index=0
        )

        assert result == {"id": "123", "value": "test", "must_exist": 1}
        assert structural_policy.calls == [{"id": "123", "value": "test"}]

    @pytest.mark.asyncio
    async def test_transform_records_shadow_comparison_for_semantic_reject(
        self, mock_context: PipelineContext
    ) -> None:
        metrics = MagicMock()
        structural_policy = _FakeStructuralPolicy(
            StructuralPolicyOutcome(record={"id": "123", "value": "test"})
        )
        transformer = ConcreteTransformer(
            provider="test",
            silver_filters=SilverFilterConfig(required_fields=("must_exist",)),
            dependencies=build_test_transformer_dependencies(
                structural_policy=structural_policy,
                metrics=metrics,
            ),
        )

        with pytest.raises(FilteredOutError):
            await transformer.transform(
                mock_context,
                {"id": "123", "value": "test"},
                index=0,
            )

        metrics.increment_counter.assert_any_call(
            "bioetl_structural_policy_shadow_comparisons_total",
            1,
            labels={
                "provider": "test",
                "entity_type": "unknown",
                "comparison": "structural_pass_semantic_reject",
            },
        )

    @pytest.mark.asyncio
    async def test_transform_records_structural_event_metrics_for_nullable_remediation(
        self, mock_context: PipelineContext
    ) -> None:
        metrics = MagicMock()
        structural_policy = _FakeStructuralPolicy(
            StructuralPolicyOutcome(
                record={
                    "id": "123",
                    "value": None,
                    "_dq_warn": True,
                    "_dq_error": False,
                },
                events=(
                    StructuralPolicyEvent(
                        level="warning",
                        event="silver_structural_type_coerced_to_null",
                        details={"field": "value"},
                    ),
                ),
            )
        )
        transformer = ConcreteTransformer(
            provider="test",
            dependencies=build_test_transformer_dependencies(
                structural_policy=structural_policy,
                metrics=metrics,
            ),
        )

        result = await transformer.transform(
            mock_context,
            {"id": "123", "value": "bad-float"},
            index=0,
        )

        assert result is not None
        metrics.increment_counter.assert_any_call(
            "bioetl_structural_policy_events_total",
            1,
            labels={
                "provider": "test",
                "entity_type": "unknown",
                "action": "nullable_type_to_null",
            },
        )

    @pytest.mark.asyncio
    async def test_transform_raises_filtered_out_error_from_structural_policy(
        self, mock_context: PipelineContext
    ) -> None:
        structural_policy = _FakeStructuralPolicy(
            StructuralPolicyOutcome(
                record={"id": "123", "value": "bad"},
                quarantine_reason="bad structural record",
                details={
                    "reason_code": "required_field_type_mismatch",
                    "field": "src_id",
                    "action_taken": "quarantine_original_record",
                },
                events=(
                    StructuralPolicyEvent(
                        level="warning",
                        event="silver_structural_type_mismatch_warn",
                        details={"field": "src_id"},
                    ),
                ),
            )
        )
        transformer = ConcreteTransformer(
            provider="test",
            dependencies=build_test_transformer_dependencies(
                structural_policy=structural_policy
            ),
        )

        with pytest.raises(FilteredOutError, match="bad structural record"):
            await transformer.transform(mock_context, {"id": "123"}, index=0)

        mock_context.logger.warning.assert_called_once()
        mock_context.logger.debug.assert_called_once()
        debug_args = mock_context.logger.debug.call_args
        assert "silver_structural_quarantined" in debug_args[0]


@pytest.mark.unit
class TestSerializeJson:
    """Tests for serialize_json static method.

    Tests the refactored serialize_json() that returns native Python types
    for single-element lists instead of converting to string.
    """

    # === None и пустые коллекции ===

    def test_none_returns_none(self) -> None:
        """Test returns None for None input."""
        assert BaseTransformer.serialize_json(None) is None

    def test_empty_list_returns_none(self) -> None:
        """Test returns None for empty list (semantic consistency)."""
        assert BaseTransformer.serialize_json([]) is None

    def test_empty_dict_returns_none(self) -> None:
        """Test returns None for empty dict (semantic consistency)."""
        assert BaseTransformer.serialize_json({}) is None

    # === Single-element lists: unwrap to native type ===

    def test_single_string_unwrapped(self) -> None:
        """Test unwraps single-element list containing string."""
        result = BaseTransformer.serialize_json(["hello"])
        assert result == "hello"
        assert isinstance(result, str)

    def test_single_int_unwrapped(self) -> None:
        """Test unwraps single-element list containing int."""
        result = BaseTransformer.serialize_json([42])
        assert result == 42
        assert isinstance(result, int)

    def test_single_float_unwrapped(self) -> None:
        """Test unwraps single-element list containing float."""
        result = BaseTransformer.serialize_json([3.14])
        assert result == pytest.approx(3.14)
        assert isinstance(result, float)

    def test_single_bool_true_unwrapped(self) -> None:
        """Test unwraps single-element list containing True."""
        result = BaseTransformer.serialize_json([True])
        assert result is True
        assert isinstance(result, bool)

    def test_single_bool_false_unwrapped(self) -> None:
        """Test unwraps single-element list containing False."""
        result = BaseTransformer.serialize_json([False])
        assert result is False
        assert isinstance(result, bool)

    def test_single_none_unwrapped(self) -> None:
        """Test unwraps single-element list containing None."""
        result = BaseTransformer.serialize_json([None])
        assert result is None

    def test_single_dict_serialized_to_json(self) -> None:
        """Test unwraps single-element list containing dict to JSON string."""
        result = BaseTransformer.serialize_json([{"a": 1, "b": 2}])
        assert result == '{"a":1,"b":2}'
        assert isinstance(result, str)

    def test_single_empty_dict_returns_none(self) -> None:
        """Test unwraps single-element list containing empty dict to None."""
        result = BaseTransformer.serialize_json([{}])
        assert result is None

    # === Multi-element lists: JSON serialize ===

    def test_multi_element_list_ints(self) -> None:
        """Test multi-element list of ints is JSON serialized."""
        result = BaseTransformer.serialize_json([1, 2, 3])
        assert result == "[1,2,3]"

    def test_multi_element_list_strings(self) -> None:
        """Test multi-element list of strings is JSON serialized."""
        result = BaseTransformer.serialize_json(["a", "b"])
        assert result == '["a","b"]'

    def test_multi_element_list_mixed(self) -> None:
        """Test multi-element list of mixed types is JSON serialized."""
        result = BaseTransformer.serialize_json([1, "two", True, None])
        assert result == '[1,"two",true,null]'

    def test_multi_element_list_dicts(self) -> None:
        """Test multi-element list of dicts is JSON serialized."""
        result = BaseTransformer.serialize_json([{"a": 1}, {"b": 2}])
        assert result == '[{"a":1},{"b":2}]'

    def test_keeps_multi_element_list_as_array(self) -> None:
        """Test keeps multi-element list as JSON array."""
        data = [{"type": "Ki"}, {"type": "IC50"}]
        result = BaseTransformer.serialize_json(data)
        assert result == '[{"type":"Ki"},{"type":"IC50"}]'

    # === Dicts: JSON serialize ===

    def test_dict_serialized_sorted_keys(self) -> None:
        """Test dict is serialized with sorted keys."""
        result = BaseTransformer.serialize_json({"z": 1, "a": 2})
        assert result == '{"a":2,"z":1}'

    def test_nested_dict(self) -> None:
        """Test nested dict is serialized correctly."""
        result = BaseTransformer.serialize_json({"outer": {"inner": 1}})
        assert result == '{"outer":{"inner":1}}'

    def test_serializes_non_empty_dict(self) -> None:
        """Test serializes non-empty dict to JSON string."""
        data = {"key": "value", "number": 42}
        result = BaseTransformer.serialize_json(data)
        assert result == '{"key":"value","number":42}'

    def test_preserves_unicode(self) -> None:
        """Test preserves unicode characters without escaping."""
        data = {"name": "Ацетаминофен", "formula": "C₈H₉NO₂"}
        result = BaseTransformer.serialize_json(data)
        assert "Ацетаминофен" in result
        assert "C₈H₉NO₂" in result

    def test_serializes_nested_structure(self) -> None:
        """Test serializes nested structures correctly."""
        data = {
            "properties": [
                {"type": "DOSE", "value": 0.0, "units": "mg/kg"},
                {"type": "TIME", "value": 3.0, "units": "hr"},
            ]
        }
        result = BaseTransformer.serialize_json(data)
        assert '"properties"' in result
        assert '"DOSE"' in result
        assert '"TIME"' in result

    # === Non-collection types: return as-is ===

    def test_string_passthrough(self) -> None:
        """Test string input is returned as-is."""
        result = BaseTransformer.serialize_json("hello")
        assert result == "hello"

    def test_int_passthrough(self) -> None:
        """Test int input is returned as-is (not converted to string)."""
        result = BaseTransformer.serialize_json(42)
        assert result == 42
        assert isinstance(result, int)

    def test_float_passthrough(self) -> None:
        """Test float input is returned as-is."""
        result = BaseTransformer.serialize_json(3.14)
        assert result == pytest.approx(3.14)
        assert isinstance(result, float)

    def test_bool_passthrough(self) -> None:
        """Test bool input is returned as-is."""
        result = BaseTransformer.serialize_json(True)
        assert result is True
        assert isinstance(result, bool)

    # === Edge cases ===

    def test_nested_single_element_list(self) -> None:
        """Test single-element list containing list is JSON-serialized."""
        result = BaseTransformer.serialize_json([[1, 2, 3]])
        assert result == "[1,2,3]"
        assert isinstance(result, str)

    def test_nested_single_element_empty_list_returns_none(self) -> None:
        """Test single-element list containing empty list returns None."""
        result = BaseTransformer.serialize_json([[]])
        assert result is None

    def test_zero_is_valid_int(self) -> None:
        """Test zero is unwrapped as valid int."""
        result = BaseTransformer.serialize_json([0])
        assert result == 0
        assert isinstance(result, int)

    def test_empty_string_is_valid(self) -> None:
        """Test empty string is unwrapped as valid string."""
        result = BaseTransformer.serialize_json([""])
        assert result == ""
        assert isinstance(result, str)

    def test_negative_number_unwrapped(self) -> None:
        """Test negative number is unwrapped correctly."""
        result = BaseTransformer.serialize_json([-42])
        assert result == -42
        assert isinstance(result, int)

    def test_float_zero_unwrapped(self) -> None:
        """Test float zero is unwrapped correctly."""
        result = BaseTransformer.serialize_json([0.0])
        assert result == pytest.approx(0.0)
        assert isinstance(result, float)


@pytest.mark.unit
class TestGoldMethods:
    """Tests for should_write_gold and transform_for_gold methods."""

    def test_should_write_gold_returns_true_without_filters(
        self, mock_context: PipelineContext
    ) -> None:
        """Test should_write_gold returns True when no filters are configured."""
        transformer = ConcreteTransformer(
            provider="test",
            dependencies=build_test_transformer_dependencies(),
        )
        record = {"field": "value"}
        assert transformer.should_write_gold(mock_context, record) is True

    def test_should_write_gold_uses_filters(
        self, mock_context: PipelineContext
    ) -> None:
        """Test should_write_gold uses injected filter configuration."""
        # GoldFilterConfig usually contains column filters
        from bioetl.domain.filtering import GoldColumnFilter

        col_filter = GoldColumnFilter(column="type", values=frozenset(["Ki"]))
        filters = GoldFilterConfig(column_filters=(col_filter,))
        transformer = ConcreteTransformer(
            provider="test",
            gold_filters=filters,
            dependencies=build_test_transformer_dependencies(),
        )

        # Matching record
        assert transformer.should_write_gold(mock_context, {"type": "Ki"}) is True

        # Non-matching record
        assert transformer.should_write_gold(mock_context, {"type": "IC50"}) is False

    def test_transform_for_gold_removes_excluded_fields(
        self, mock_context: PipelineContext
    ) -> None:
        """Test transform_for_gold removes defined excluded fields.

        Note: BaseTransformer.GOLD_EXCLUDE_FIELDS is empty by default.
        Column filtering now happens in BatchWriter.write_gold() based on Gold schema.
        This test uses a custom transformer with GOLD_EXCLUDE_FIELDS to test the behavior.
        """

        class TransformerWithExclusions(ConcreteTransformer):
            GOLD_EXCLUDE_FIELDS = frozenset({"content_hash", "molecule_properties"})

        transformer = TransformerWithExclusions(
            provider="test",
            dependencies=build_test_transformer_dependencies(),
        )
        silver_record = {
            "valid_field": "keep_me",
            "content_hash": "remove_me",
            "_run_id": "keep_me_too",
            "molecule_properties": "remove_me_too",
        }

        gold_record = transformer.transform_for_gold(mock_context, silver_record)

        assert "valid_field" in gold_record
        assert "_run_id" in gold_record
        assert "content_hash" not in gold_record
        assert "molecule_properties" not in gold_record


@pytest.mark.unit
class TestValidateValueObject:
    """Tests for validate_value_object() and validate_value_objects() helper methods."""

    def test_validate_value_object_returns_string_for_valid(self) -> None:
        """Test validate_value_object returns string for valid DOI."""
        from bioetl.domain.value_objects import DOI

        result = BaseTransformer.validate_value_object(DOI, "10.1038/nature12373")
        assert result == "10.1038/nature12373"
        assert isinstance(result, str)

    def test_validate_value_object_returns_none_for_invalid(self) -> None:
        """Test validate_value_object returns None for invalid DOI."""
        from bioetl.domain.value_objects import DOI

        result = BaseTransformer.validate_value_object(DOI, "invalid-doi")
        assert result is None

    def test_validate_value_object_returns_none_for_none(self) -> None:
        """Test validate_value_object returns None for None input."""
        from bioetl.domain.value_objects import DOI

        result = BaseTransformer.validate_value_object(DOI, None)
        assert result is None

    def test_validate_value_object_returns_none_for_empty_string(self) -> None:
        """Test validate_value_object returns None for empty string."""
        from bioetl.domain.value_objects import DOI

        result = BaseTransformer.validate_value_object(DOI, "")
        assert result is None

    def test_validate_value_object_as_value_returns_int(self) -> None:
        """Test validate_value_object with as_string=False returns value directly."""
        from bioetl.domain.value_objects import PublicationYear

        result = BaseTransformer.validate_value_object(
            PublicationYear, 2020, as_string=False
        )
        assert result == 2020
        assert isinstance(result, int)

    def test_validate_value_object_strips_url_prefix(self) -> None:
        """Test validate_value_object handles DOI with URL prefix."""
        from bioetl.domain.value_objects import DOI

        result = BaseTransformer.validate_value_object(
            DOI, "https://doi.org/10.1038/nature12373"
        )
        # DOI normalizes to lowercase
        assert result == "10.1038/nature12373"

    def test_validate_value_object_inchi_key_valid(self) -> None:
        """Test validate_value_object with valid InChIKey."""
        from bioetl.domain.value_objects import InChIKey

        result = BaseTransformer.validate_value_object(
            InChIKey, "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"
        )
        assert result == "BSYNRYMUTXBXSQ-UHFFFAOYSA-N"

    def test_validate_value_object_inchi_key_invalid(self) -> None:
        """Test validate_value_object with invalid InChIKey."""
        from bioetl.domain.value_objects import InChIKey

        result = BaseTransformer.validate_value_object(InChIKey, "not-an-inchi_key")
        assert result is None

    def test_validate_value_objects_returns_list(self) -> None:
        """Test validate_value_objects returns list of validated values."""
        from bioetl.domain.value_objects import TaxonomyId

        result = BaseTransformer.validate_value_objects(
            TaxonomyId, [9606, 10090], as_string=False
        )
        assert result == [9606, 10090]

    def test_validate_value_objects_filters_invalid(self) -> None:
        """Test validate_value_objects filters out invalid values."""
        from bioetl.domain.value_objects import TaxonomyId

        result = BaseTransformer.validate_value_objects(
            TaxonomyId, [9606, -1, 10090], as_string=False
        )
        # -1 is invalid taxonomy ID (negative)
        assert result == [9606, 10090]

    def test_validate_value_objects_returns_none_for_empty(self) -> None:
        """Test validate_value_objects returns None for empty list."""
        from bioetl.domain.value_objects import TaxonomyId

        result = BaseTransformer.validate_value_objects(TaxonomyId, [])
        assert result is None

    def test_validate_value_objects_returns_none_for_none(self) -> None:
        """Test validate_value_objects returns None for None input."""
        from bioetl.domain.value_objects import TaxonomyId

        result = BaseTransformer.validate_value_objects(TaxonomyId, None)
        assert result is None

    def test_validate_value_objects_returns_none_if_all_invalid(self) -> None:
        """Test validate_value_objects returns None if all values invalid."""
        from bioetl.domain.value_objects import TaxonomyId

        result = BaseTransformer.validate_value_objects(
            TaxonomyId, [-1, -2], as_string=False
        )
        assert result is None

    def test_validate_value_objects_as_string(self) -> None:
        """Test validate_value_objects with as_string=True."""
        from bioetl.domain.value_objects import TaxonomyId

        result = BaseTransformer.validate_value_objects(
            TaxonomyId, [9606, 10090], as_string=True
        )
        assert result == ["9606", "10090"]
