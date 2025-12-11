"""
Value Objects for cryptographic primitives.

This module contains value objects for cryptographic hash digests
with proper validation and immutability guarantees.
"""

from __future__ import annotations

import re

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

__all__ = [
    "HashDigest",
]


class HashDigest:
    """Value Object для BLAKE2b-256 хеш-дайджеста (64 hex символа)."""

    __slots__ = ("_value",)
    _pattern = re.compile(r"^[a-f0-9]{64}$")

    def __init__(self, value: str) -> None:
        normalized = value.lower()
        if not self._pattern.match(normalized):
            raise ValueError(
                f"Invalid HashDigest: '{value}'. "
                f"Expected 64 lowercase hex characters (BLAKE2b-256)"
            )
        self._value = normalized

    def __setattr__(self, name: str, value: object) -> None:
        if name == "_value" and hasattr(self, "_value"):
            raise AttributeError("HashDigest is immutable")
        super().__setattr__(name, value)

    @property
    def value(self) -> str:
        """String representation of HashDigest."""
        return self._value

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"HashDigest({self._value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, HashDigest):
            return self._value == other._value
        return NotImplemented

    def __hash__(self) -> int:
        return hash(self._value)

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: type, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.no_info_after_validator_function(
            cls,
            core_schema.str_schema(),
            serialization=core_schema.plain_serializer_function_ser_schema(str),
        )
