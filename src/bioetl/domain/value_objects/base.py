"""Base class for Value Objects.

Value Objects are immutable domain primitives that encapsulate validation
and business rules. They provide type safety and self-validation.

Characteristics:
- Immutable (frozen dataclasses or __slots__ with immutability enforcement)
- Equality by value (not by identity)
- Validation in constructor
- No identity (unlike Entities)

See DDD patterns: https://martinfowler.com/bliki/ValueObject.html
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeVar, override

__all__ = [
    "T",
    "ValueObject",
]


T = TypeVar("T")


class ValueObject[T](ABC):
    """Base class for Value Objects with single wrapped value.

    Provides immutability, value equality, and validation.
    Subclasses must implement _validate() to enforce domain rules.

    Attributes:
        _value: The validated internal value.
    """

    __slots__ = ("_value", "_initialized")

    _value: T  # Type annotation for mypy

    def __init__(self, value: T) -> None:
        """Create a Value Object with validated value.

        Args:
            value: Raw value to validate and store.

        Raises:
            ValueError: If validation fails.
        """
        object.__setattr__(self, "_initialized", False)
        validated = self._validate(value)
        object.__setattr__(self, "_value", validated)
        object.__setattr__(self, "_initialized", True)

    @property
    def value(self) -> T:
        """Get the internal value."""
        return self._value

    @abstractmethod
    def _validate(self, value: T) -> T:
        """Validate and normalize the input value.

        Args:
            value: Raw value to validate.

        Returns:
            Normalized/validated value.

        Raises:
            ValueError: If validation fails.
        """
        ...

    @override
    def __eq__(self, other: object) -> bool:
        """Compare by value, not identity."""
        if not isinstance(other, self.__class__):
            return NotImplemented
        return bool(self._value == other._value)

    @override
    def __hash__(self) -> int:
        """Hash based on class and value."""
        return hash((self.__class__.__name__, self._value))

    @override
    def __repr__(self) -> str:
        """String representation showing class and value."""
        return f"{self.__class__.__name__}({self._value!r})"

    @override
    def __str__(self) -> str:
        """String representation of the value."""
        return str(self._value)

    @override
    def __setattr__(
        self,
        name: str,
        value: Any,  # Any: Python __setattr__ protocol requires Any
    ) -> None:
        """Prevent mutation of Value Object."""
        if getattr(self, "_initialized", False):
            raise AttributeError(f"{self.__class__.__name__} is immutable")
        object.__setattr__(self, name, value)

    @override
    def __delattr__(self, name: str) -> None:
        """Prevent deletion of attributes."""
        raise AttributeError(f"{self.__class__.__name__} is immutable")
