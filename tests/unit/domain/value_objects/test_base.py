"""Tests for base Value Object class."""

from __future__ import annotations

import pytest

from bioetl.domain.value_objects.base import ValueObject


class ConcreteValueObject(ValueObject[str]):
    """Concrete implementation for testing."""

    def _validate(self, value: str) -> str:
        if not isinstance(value, str):
            raise ValueError(f"Expected str, got {type(value).__name__}")
        normalized = value.strip().upper()
        if not normalized:
            raise ValueError("Value cannot be empty")
        return normalized


class TestValueObject:
    """Tests for ValueObject base class."""

    def test_creation(self) -> None:
        """Test basic creation."""
        vo = ConcreteValueObject("test")
        assert vo.value == "TEST"

    def test_validation_is_called(self) -> None:
        """Test that _validate is called during creation."""
        vo = ConcreteValueObject("  hello  ")
        # Should be normalized (stripped and uppercased)
        assert vo.value == "HELLO"

    def test_validation_raises_on_invalid(self) -> None:
        """Test that ValueError propagates from _validate."""
        with pytest.raises(ValueError, match="cannot be empty"):
            ConcreteValueObject("")

    def test_immutability_setattr(self) -> None:
        """Test that setting attributes raises AttributeError."""
        vo = ConcreteValueObject("test")
        with pytest.raises(AttributeError, match="immutable"):
            vo._value = "other"  # type: ignore[misc]

    def test_immutability_delattr(self) -> None:
        """Test that deleting attributes raises AttributeError."""
        vo = ConcreteValueObject("test")
        with pytest.raises(AttributeError, match="immutable"):
            del vo._value

    def test_equality_same_value(self) -> None:
        """Test equality for same values."""
        vo1 = ConcreteValueObject("test")
        vo2 = ConcreteValueObject("test")
        assert vo1 == vo2
        assert vo1 is not vo2

    def test_equality_different_input_same_value(self) -> None:
        """Test equality when inputs normalize to same value."""
        vo1 = ConcreteValueObject("TEST")
        vo2 = ConcreteValueObject("  test  ")
        assert vo1 == vo2

    def test_inequality_different_values(self) -> None:
        """Test inequality for different values."""
        vo1 = ConcreteValueObject("test")
        vo2 = ConcreteValueObject("other")
        assert vo1 != vo2

    def test_inequality_with_different_types(self) -> None:
        """Test inequality with different types."""
        vo = ConcreteValueObject("test")
        assert vo != "TEST"
        assert vo != 123
        assert vo is not None

    def test_hash_consistent_with_equality(self) -> None:
        """Test hash is consistent with equality."""
        vo1 = ConcreteValueObject("test")
        vo2 = ConcreteValueObject("test")
        assert hash(vo1) == hash(vo2)

    def test_hash_different_for_different_values(self) -> None:
        """Test hash is different for different values."""
        vo1 = ConcreteValueObject("test")
        vo2 = ConcreteValueObject("other")
        # Note: This could theoretically fail due to hash collisions,
        # but for simple strings it should work
        assert hash(vo1) != hash(vo2)

    def test_can_be_used_in_set(self) -> None:
        """Test Value Objects can be used in sets."""
        s = {
            ConcreteValueObject("a"),
            ConcreteValueObject("a"),
            ConcreteValueObject("b"),
        }
        assert len(s) == 2

    def test_can_be_used_as_dict_key(self) -> None:
        """Test Value Objects can be used as dict keys."""
        d = {ConcreteValueObject("key"): "value"}
        assert d[ConcreteValueObject("key")] == "value"
        assert d[ConcreteValueObject("  KEY  ")] == "value"  # Normalized

    def test_repr(self) -> None:
        """Test repr shows class name and value."""
        vo = ConcreteValueObject("test")
        assert repr(vo) == "ConcreteValueObject('TEST')"

    def test_str(self) -> None:
        """Test str returns the string representation of value."""
        vo = ConcreteValueObject("test")
        assert str(vo) == "TEST"


class IntValueObject(ValueObject[int]):
    """Concrete implementation with int value for testing."""

    def _validate(self, value: int) -> int:
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"Expected int, got {type(value).__name__}")
        if value < 0:
            raise ValueError("Value must be non-negative")
        return value


class TestValueObjectWithInt:
    """Tests for ValueObject with int type."""

    def test_creation(self) -> None:
        """Test basic creation with int."""
        vo = IntValueObject(42)
        assert vo.value == 42

    def test_validation_raises_on_negative(self) -> None:
        """Test validation rejects negative values."""
        with pytest.raises(ValueError, match="non-negative"):
            IntValueObject(-1)

    def test_equality(self) -> None:
        """Test equality for int values."""
        vo1 = IntValueObject(42)
        vo2 = IntValueObject(42)
        assert vo1 == vo2

    def test_hash(self) -> None:
        """Test hash for int values."""
        vo1 = IntValueObject(42)
        vo2 = IntValueObject(42)
        assert hash(vo1) == hash(vo2)

    def test_str(self) -> None:
        """Test str returns string representation of int."""
        vo = IntValueObject(42)
        assert str(vo) == "42"
