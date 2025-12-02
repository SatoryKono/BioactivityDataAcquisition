import pandas as pd
import pandera.pandas as pa
import pytest
from unittest.mock import patch, MagicMock
from bioetl.validation.service import ValidationService
from bioetl.validation.impl.pandera_validator import PanderaValidatorImpl


# Define a dummy schema for testing
class TestSchema(pa.DataFrameModel):
    id: int = pa.Field(ge=0)
    name: str = pa.Field()


def test_validation_service_success():
    # Arrange
    service = ValidationService()
    df = pd.DataFrame({"id": [1, 2], "name": ["a", "b"]})

    # Mock registry to return TestSchema
    with patch("bioetl.validation.service.registry") as mock_registry:
        mock_registry.get_schema.return_value = TestSchema

        # Act
        result = service.validate(df, "test_entity")

        # Assert
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 2
        mock_registry.get_schema.assert_called_with("test_entity")


def test_validation_service_failure():
    # Arrange
    service = ValidationService()
    df = pd.DataFrame({"id": [-1], "name": ["a"]})  # Invalid id

    with patch("bioetl.validation.service.registry") as mock_registry:
        mock_registry.get_schema.return_value = TestSchema

        # Act & Assert
        with pytest.raises(
            ValueError,
            match="Validation failed for test_entity"
        ):
            service.validate(df, "test_entity")


def test_pandera_validator_impl():
    # Arrange
    validator = PanderaValidatorImpl(TestSchema)
    df_valid = pd.DataFrame({"id": [1], "name": ["test"]})
    df_invalid = pd.DataFrame({"id": [-1], "name": ["test"]})

    # Test validate() success
    result = validator.validate(df_valid)
    assert result.is_valid
    assert not result.errors

    # Test validate() failure
    result_fail = validator.validate(df_invalid)
    assert not result_fail.is_valid
    assert result_fail.errors

    # Test is_valid()
    assert validator.is_valid(df_valid)
    assert not validator.is_valid(df_invalid)


def test_pandera_validator_exception():
    # Mock schema to raise generic exception
    mock_schema = MagicMock()
    mock_schema.validate.side_effect = Exception("Generic error")

    validator = PanderaValidatorImpl(mock_schema)
    df = pd.DataFrame({"id": [1]})

    result = validator.validate(df)
    assert not result.is_valid
    assert "Generic error" in result.errors[0]
