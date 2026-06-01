# tests/unit/application/pipelines/test_chembl_assay_parameters.py
"""Unit tests for ChEMBL AssayParameters entity and transformer."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.application.pipelines.chembl.assay_parameters_transformer import (
    AssayParametersTransformer,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.entities.chembl_assay_parameters import AssayParameters
from bioetl.domain.types import RunType
from tests.helpers.transformer_dependencies import build_test_transformer_dependencies


@pytest.fixture
def mock_context():
    """Create a mock pipeline context."""
    mock_logger = MagicMock()
    mock_logger.bind = MagicMock(return_value=mock_logger)
    mock_logger.warning = MagicMock()
    mock_logger.debug = MagicMock()
    return PipelineContext(
        run_id=uuid4(),
        run_type=RunType.INCREMENTAL,
        logger=mock_logger,
    )


# =============================================================================
# AssayParameters Entity Tests
# =============================================================================


@pytest.mark.unit
class TestAssayParametersEntity:
    """Tests for AssayParameters domain entity."""

    @pytest.fixture
    def valid_params(self) -> dict:
        """Create valid AssayParameters constructor arguments."""
        return {
            "assay_param_id": 12345,
            "assay_id": "CHEMBL1217643",
            "type": "CONC",
            "entity_id": "chembl:12345",
            "content_hash": "a" * 64,
            "run_id": uuid4(),
            "run_type": RunType.INCREMENTAL,
            "ingestion_ts": MagicMock(),  # Mock datetime
            "_index": 0,
        }

    def test_create_valid_entity(self, valid_params: dict) -> None:
        """Test creating valid AssayParameters entity."""
        entity = AssayParameters(**valid_params)

        assert entity.assay_param_id == 12345
        assert entity.assay_id == "CHEMBL1217643"
        assert entity.type == "CONC"

    def test_create_entity_with_values(self, valid_params: dict) -> None:
        """Test creating AssayParameters with numeric and text values."""
        valid_params["value"] = 10.0
        valid_params["units"] = "uM"
        valid_params["standard_value"] = 10000.0
        valid_params["standard_units"] = "nM"

        entity = AssayParameters(**valid_params)

        assert entity.value == pytest.approx(10.0)
        assert entity.units == "uM"
        assert entity.standard_value == pytest.approx(10000.0)
        assert entity.standard_units == "nM"

    def test_invalid_assay_param_id_zero(self, valid_params: dict) -> None:
        """Test that assay_param_id=0 raises ValueError."""
        valid_params["assay_param_id"] = 0

        with pytest.raises(ValueError, match="assay_param_id must be positive"):
            AssayParameters(**valid_params)

    def test_invalid_assay_param_id_negative(self, valid_params: dict) -> None:
        """Test that negative assay_param_id raises ValueError."""
        valid_params["assay_param_id"] = -1

        with pytest.raises(ValueError, match="assay_param_id must be positive"):
            AssayParameters(**valid_params)

    def test_invalid_chembl_id_format(self, valid_params: dict) -> None:
        """Test that invalid ChEMBL ID format raises ValueError."""
        valid_params["assay_id"] = "INVALID123"

        with pytest.raises(ValueError, match="Invalid assay_id"):
            AssayParameters(**valid_params)

    def test_missing_type_allowed(self, valid_params: dict) -> None:
        """Test that empty/None type is allowed (no sentinel value)."""
        valid_params["type"] = ""
        entity = AssayParameters(**valid_params)
        assert entity.type == ""

        valid_params["type"] = None
        entity = AssayParameters(**valid_params)
        assert entity.type is None

    def test_has_numeric_value_with_value(self, valid_params: dict) -> None:
        """Test has_numeric_value returns True when value is present."""
        valid_params["value"] = 10.0
        entity = AssayParameters(**valid_params)

        assert entity.has_numeric_value() is True

    def test_has_numeric_value_with_standard_value(self, valid_params: dict) -> None:
        """Test has_numeric_value returns True when standard_value is present."""
        valid_params["standard_value"] = 10000.0
        entity = AssayParameters(**valid_params)

        assert entity.has_numeric_value() is True

    def test_has_numeric_value_without_values(self, valid_params: dict) -> None:
        """Test has_numeric_value returns False when no numeric values."""
        entity = AssayParameters(**valid_params)

        assert entity.has_numeric_value() is False

    def test_has_text_value_with_text(self, valid_params: dict) -> None:
        """Test has_text_value returns True when text_value is present."""
        valid_params["text_value"] = "Room temperature"
        entity = AssayParameters(**valid_params)

        assert entity.has_text_value() is True

    def test_has_text_value_with_standard_text(self, valid_params: dict) -> None:
        """Test has_text_value returns True when standard_text_value is present."""
        valid_params["standard_text_value"] = "Room temperature"
        entity = AssayParameters(**valid_params)

        assert entity.has_text_value() is True

    def test_has_text_value_without_text(self, valid_params: dict) -> None:
        """Test has_text_value returns False when no text values."""
        entity = AssayParameters(**valid_params)

        assert entity.has_text_value() is False

    def test_get_comparable_value_prefers_standard(self, valid_params: dict) -> None:
        """Test get_comparable_value prefers standardized values."""
        valid_params["value"] = 10.0
        valid_params["units"] = "uM"
        valid_params["standard_value"] = 10000.0
        valid_params["standard_units"] = "nM"

        entity = AssayParameters(**valid_params)
        value, units = entity.get_comparable_value()

        assert value == pytest.approx(10000.0)
        assert units == "nM"

    def test_get_comparable_value_falls_back_to_raw(self, valid_params: dict) -> None:
        """Test get_comparable_value falls back to raw values."""
        valid_params["value"] = 10.0
        valid_params["units"] = "uM"

        entity = AssayParameters(**valid_params)
        value, units = entity.get_comparable_value()

        assert value == pytest.approx(10.0)
        assert units == "uM"

    def test_get_comparable_value_returns_none(self, valid_params: dict) -> None:
        """Test get_comparable_value returns None when no values."""
        entity = AssayParameters(**valid_params)
        value, units = entity.get_comparable_value()

        assert value is None
        assert units is None


# =============================================================================
# AssayParametersTransformer Tests
# =============================================================================


@pytest.mark.unit
class TestAssayParametersTransformer:
    """Tests for AssayParametersTransformer."""

    @pytest.fixture
    def transformer(self) -> AssayParametersTransformer:
        """Create AssayParametersTransformer instance."""
        return AssayParametersTransformer(
            provider="chembl", dependencies=build_test_transformer_dependencies()
        )

    @pytest.fixture
    def sample_record(self) -> dict:
        """Create sample Bronze record from ChEMBL API."""
        return {
            "assay_param_id": 12345,
            "assay_id": "CHEMBL1217643",
            "type": "CONC",
            "relation": "=",
            "value": 10.0,
            "units": "uM",
            "text_value": None,
            "comments": "Final compound concentration",
            "standard_type": "CONC",
            "standard_relation": "=",
            "standard_value": 10000.0,
            "standard_units": "nM",
            "standard_text_value": None,
        }

    @pytest.mark.asyncio
    async def test_parameters_transformer__valid_record__2dc9241c(
        self,
        transformer: AssayParametersTransformer,
        mock_context,
        sample_record: dict,
    ) -> None:
        """Test transformation of valid assay parameters record."""
        result = await transformer.transform(mock_context, sample_record, index=0)

        assert result is not None
        assert result["assay_param_id"] == 12345
        assert result["assay_id"] == "CHEMBL1217643"
        assert result["type"] == "CONC"
        assert result["value"] == pytest.approx(10.0)
        assert result["standard_value"] == pytest.approx(10000.0)
        assert "entity_id" in result
        assert "content_hash" in result
        assert "_run_id" in result

    @pytest.mark.asyncio
    async def test_transform_missing_assay_param_id(
        self,
        transformer: AssayParametersTransformer,
        mock_context,
    ) -> None:
        """Test transformation returns None when assay_param_id is missing."""
        record = {
            "assay_id": "CHEMBL1217643",
            "type": "CONC",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is None

    @pytest.mark.asyncio
    async def test_transform_with_text_value(
        self,
        transformer: AssayParametersTransformer,
        mock_context,
    ) -> None:
        """Test transformation with text value instead of numeric."""
        record = {
            "assay_param_id": 12346,
            "assay_id": "CHEMBL1217643",
            "type": "TEMP",
            "text_value": "Room temperature",
            "standard_text_value": "25 degrees Celsius",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["text_value"] == "Room temperature"
        assert result["standard_text_value"] == "25 degrees Celsius"
        assert result["value"] is None

    @pytest.mark.asyncio
    async def test_transform_leaves_type_canonicalization_to_profile(
        self,
        transformer: AssayParametersTransformer,
        mock_context,
    ) -> None:
        """Transformer maps source values; profile layer owns type canonicalization."""
        record = {
            "assay_param_id": 12347,
            "assay_id": "CHEMBL1217643",
            "type": "conc",  # lowercase
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["type"] == "conc"

    @pytest.mark.asyncio
    async def test_transform_handles_none_type(
        self,
        transformer: AssayParametersTransformer,
        mock_context,
    ) -> None:
        """Test that None type remains None (no sentinel value)."""
        record = {
            "assay_param_id": 12348,
            "assay_id": "CHEMBL1217643",
            "type": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["type"] is None

    @pytest.mark.asyncio
    async def test_transform_all_optional_fields_none(
        self,
        transformer: AssayParametersTransformer,
        mock_context,
    ) -> None:
        """Test transformation with all optional fields as None."""
        record = {
            "assay_param_id": 12349,
            "assay_id": "CHEMBL1217643",
            "type": "CONC",
            "relation": None,
            "value": None,
            "units": None,
            "text_value": None,
            "comments": None,
            "standard_type": None,
            "standard_relation": None,
            "standard_value": None,
            "standard_units": None,
            "standard_text_value": None,
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert result["relation"] is None
        assert result["value"] is None
        assert result["units"] is None
        assert result["text_value"] is None

    @pytest.mark.asyncio
    async def test_parameters_transformer__custom_provider__60817433(
        self,
        mock_context,
    ) -> None:
        """Test transformation with custom provider."""
        transformer = AssayParametersTransformer(
            provider="custom_provider",
            dependencies=build_test_transformer_dependencies(),
        )
        record = {
            "assay_param_id": 12350,
            "assay_id": "CHEMBL1217643",
            "type": "PH",
        }

        result = await transformer.transform(mock_context, record, index=0)

        assert result is not None
        assert "entity_id" in result

    def test_has_any_value_with_numeric(
        self,
        transformer: AssayParametersTransformer,
    ) -> None:
        """Test _has_any_value returns True with numeric value."""
        record = {"value": 10.0}
        assert transformer._has_any_value(record) is True

    def test_has_any_value_with_text(
        self,
        transformer: AssayParametersTransformer,
    ) -> None:
        """Test _has_any_value returns True with text value."""
        record = {"text_value": "Room temperature"}
        assert transformer._has_any_value(record) is True

    def test_has_any_value_with_standard_value(
        self,
        transformer: AssayParametersTransformer,
    ) -> None:
        """Test _has_any_value returns True with standard value."""
        record = {"standard_value": 10000.0}
        assert transformer._has_any_value(record) is True

    def test_has_any_value_with_standard_text(
        self,
        transformer: AssayParametersTransformer,
    ) -> None:
        """Test _has_any_value returns True with standard text value."""
        record = {"standard_text_value": "Normalized temp"}
        assert transformer._has_any_value(record) is True

    def test_has_any_value_empty(
        self,
        transformer: AssayParametersTransformer,
    ) -> None:
        """Test _has_any_value returns False when no values present."""
        record = {}
        assert transformer._has_any_value(record) is False

    def test_has_any_value_all_none(
        self,
        transformer: AssayParametersTransformer,
    ) -> None:
        """Test _has_any_value returns False when all values are None."""
        record = {
            "value": None,
            "text_value": None,
            "standard_value": None,
            "standard_text_value": None,
        }
        assert transformer._has_any_value(record) is False
