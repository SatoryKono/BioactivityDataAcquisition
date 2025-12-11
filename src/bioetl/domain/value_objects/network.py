"""
Value Objects for network-related types.

This module contains value objects for URLs and other network primitives
with proper validation and normalization.
"""

from __future__ import annotations

from urllib.parse import urlparse

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

__all__ = [
    "HttpUrl",
]


class HttpUrl:
    """Value Object для HTTP/HTTPS URL с валидацией и нормализацией."""

    __slots__ = ("_value", "_scheme", "_host", "_path")
    _allowed_schemes = frozenset({"http", "https"})

    def __init__(self, value: str) -> None:
        normalized = value.strip()
        if not normalized:
            raise ValueError("HttpUrl cannot be empty")

        parsed = urlparse(normalized)

        if not parsed.scheme:
            raise ValueError(f"HttpUrl must have a scheme: '{value}'")
        if parsed.scheme.lower() not in self._allowed_schemes:
            raise ValueError(
                f"HttpUrl scheme must be http or https, got: '{parsed.scheme}'"
            )
        if not parsed.netloc:
            raise ValueError(f"HttpUrl must have a host: '{value}'")

        self._scheme = parsed.scheme.lower()
        self._host = parsed.netloc.lower()
        # Нормализация path: удаляем trailing slash, если он не единственный символ
        path = parsed.path
        if path and path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        self._path = path or "/"

        # Сборка нормализованного URL
        query = f"?{parsed.query}" if parsed.query else ""
        fragment = f"#{parsed.fragment}" if parsed.fragment else ""
        self._value = f"{self._scheme}://{self._host}{self._path}{query}{fragment}"

    def __setattr__(self, name: str, value: object) -> None:
        if hasattr(self, "_value") and name in ("_value", "_scheme", "_host", "_path"):
            raise AttributeError("HttpUrl is immutable")
        super().__setattr__(name, value)

    @property
    def value(self) -> str:
        """Normalized URL string."""
        return self._value

    @property
    def scheme(self) -> str:
        """URL scheme (http or https)."""
        return self._scheme

    @property
    def host(self) -> str:
        """URL host (including port if specified)."""
        return self._host

    @property
    def path(self) -> str:
        """URL path (normalized, without trailing slash)."""
        return self._path

    def __str__(self) -> str:
        return self._value

    def __repr__(self) -> str:
        return f"HttpUrl({self._value!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, HttpUrl):
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
