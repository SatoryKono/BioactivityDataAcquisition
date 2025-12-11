"""Tests for domain value objects."""

from pydantic import BaseModel
import pytest

from bioetl.domain.value_objects import StageName


class TestStageName:
    """Tests for StageName value object."""

    # --- Valid values ---

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("extract", "extract"),
            ("transform", "transform"),
            ("validate", "validate"),
            ("export", "export"),
        ],
    )
    def test_valid_values(self, value: str, expected: str) -> None:
        """Test that valid stage names are accepted."""
        stage = StageName(value)
        assert stage.value == expected
        assert str(stage) == expected

    # --- Case insensitivity ---

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("EXTRACT", "extract"),
            ("Extract", "extract"),
            ("TRANSFORM", "transform"),
            ("Transform", "transform"),
            ("VALIDATE", "validate"),
            ("Validate", "validate"),
            ("EXPORT", "export"),
            ("Export", "export"),
        ],
    )
    def test_case_insensitive(self, value: str, expected: str) -> None:
        """Test that stage names are case-insensitive."""
        stage = StageName(value)
        assert stage.value == expected

    # --- Alias support ---

    @pytest.mark.parametrize(
        "alias,canonical",
        [
            ("load", "export"),
            ("Load", "export"),
            ("LOAD", "export"),
        ],
    )
    def test_alias_load_to_export(self, alias: str, canonical: str) -> None:
        """Test that 'load' is an alias for 'export'."""
        stage = StageName(alias)
        assert stage.value == canonical
        assert stage == StageName.EXPORT

    # --- Invalid values ---

    @pytest.mark.parametrize(
        "invalid_value",
        [
            "fetch",
            "normalize",
            "invalid",
            "",
            "extract_data",
            "transform_records",
        ],
    )
    def test_invalid_values_raise_error(self, invalid_value: str) -> None:
        """Test that invalid stage names raise ValueError."""
        with pytest.raises(ValueError, match="Invalid stage name"):
            StageName(invalid_value)

    def test_invalid_type_raises_error(self) -> None:
        """Test that non-string input raises TypeError."""
        with pytest.raises(TypeError, match="StageName requires str"):
            StageName(123)  # type: ignore[arg-type]

    # --- Enum-like class constants ---

    def test_extract_constant(self) -> None:
        """Test StageName.EXTRACT constant."""
        assert StageName.EXTRACT.value == "extract"
        assert StageName.EXTRACT == StageName("extract")

    def test_transform_constant(self) -> None:
        """Test StageName.TRANSFORM constant."""
        assert StageName.TRANSFORM.value == "transform"
        assert StageName.TRANSFORM == StageName("transform")

    def test_validate_constant(self) -> None:
        """Test StageName.VALIDATE constant."""
        assert StageName.VALIDATE.value == "validate"
        assert StageName.VALIDATE == StageName("validate")

    def test_export_constant(self) -> None:
        """Test StageName.EXPORT constant."""
        assert StageName.EXPORT.value == "export"
        assert StageName.EXPORT == StageName("export")

    # --- all_values method ---

    def test_all_values(self) -> None:
        """Test all_values returns all allowed stage names."""
        values = StageName.all_values()
        assert values == frozenset({"extract", "transform", "validate", "export"})

    # --- Equality and hashing ---

    def test_equality_same_value(self) -> None:
        """Test that two StageName with same value are equal."""
        assert StageName("extract") == StageName("extract")
        assert StageName("EXTRACT") == StageName("extract")

    def test_equality_different_value(self) -> None:
        """Test that two StageName with different values are not equal."""
        assert StageName("extract") != StageName("transform")

    def test_equality_with_non_stagename(self) -> None:
        """Test that StageName is not equal to non-StageName."""
        assert (StageName("extract") == "extract") is False
        assert StageName("extract").__eq__("extract") is NotImplemented

    def test_hashable(self) -> None:
        """Test that StageName is hashable and can be used in sets."""
        stages = {StageName("extract"), StageName("EXTRACT"), StageName("transform")}
        assert len(stages) == 2  # extract and EXTRACT are the same

    def test_usable_as_dict_key(self) -> None:
        """Test that StageName can be used as dictionary key."""
        data = {StageName.EXTRACT: "extraction complete"}
        assert data[StageName("extract")] == "extraction complete"

    # --- String representation ---

    def test_str_representation(self) -> None:
        """Test __str__ returns the value."""
        assert str(StageName("extract")) == "extract"

    def test_repr_representation(self) -> None:
        """Test __repr__ returns a developer-friendly string."""
        assert repr(StageName("extract")) == "StageName('extract')"

    # --- Pydantic integration ---

    def test_pydantic_model_validation(self) -> None:
        """Test StageName works with Pydantic models."""

        class TestModel(BaseModel):
            stage: StageName

        model = TestModel(stage="extract")
        assert model.stage == StageName.EXTRACT
        assert model.stage.value == "extract"

    def test_pydantic_model_case_insensitive(self) -> None:
        """Test Pydantic model accepts case-insensitive values."""

        class TestModel(BaseModel):
            stage: StageName

        model = TestModel(stage="EXTRACT")
        assert model.stage.value == "extract"

    def test_pydantic_model_alias(self) -> None:
        """Test Pydantic model resolves aliases."""

        class TestModel(BaseModel):
            stage: StageName

        model = TestModel(stage="load")
        assert model.stage.value == "export"

    def test_pydantic_model_serialization(self) -> None:
        """Test StageName serializes to string in Pydantic."""

        class TestModel(BaseModel):
            stage: StageName

        model = TestModel(stage="extract")
        assert model.model_dump() == {"stage": "extract"}

    def test_pydantic_model_invalid_value(self) -> None:
        """Test Pydantic model rejects invalid stage names."""
        from pydantic import ValidationError

        class TestModel(BaseModel):
            stage: StageName

        with pytest.raises(ValidationError):
            TestModel(stage="invalid_stage")

    # --- Immutability ---

    def test_immutability(self) -> None:
        """Test that StageName instances are immutable."""
        stage = StageName("extract")
        with pytest.raises(AttributeError):
            stage._value = "transform"  # type: ignore[misc]
