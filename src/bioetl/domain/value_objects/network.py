"""Value Objects for network primitives.

Contains type-safe wrappers for URLs and network addresses.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from pydantic import GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


class HttpUrl:
    """Value Object for HTTP/HTTPS URL with validation and normalization."""

    __slots__ = ("_value", "_scheme", "_host", "_path")
    _allowed_schemes = frozenset({"http", "https"})

    def _validate_parsed_url(self, parsed: Any, original_value: str) -> None:
        """Validate parsed URL components."""
        if not parsed.scheme:
            raise ValueError(f"HttpUrl must have a scheme: '{original_value}'")
        if parsed.scheme.lower() not in self._allowed_schemes:
            raise ValueError(
                f"HttpUrl scheme must be http or https, got: '{parsed.scheme}'"
            )
        if not parsed.netloc:
            raise ValueError(f"HttpUrl must have a host: '{original_value}'")

    def _normalize_path(self, path: str) -> str:
        """Normalize URL path: remove trailing slash unless it's the only character."""
        if path and path != "/" and path.endswith("/"):
            return path.rstrip("/")
        return path or "/"

    def _assemble_url(
        self, scheme: str, host: str, path: str, query: str, fragment: str
    ) -> str:
        """Assemble normalized URL from components."""
        query_str = f"?{query}" if query else ""
        fragment_str = f"#{fragment}" if fragment else ""
        return f"{scheme}://{host}{path}{query_str}{fragment_str}"

    def __init__(self, value: str) -> None:
        normalized = value.strip()
        if not normalized:
            raise ValueError("HttpUrl cannot be empty")

        parsed = urlparse(normalized)
        self._validate_parsed_url(parsed, value)

        self._scheme = parsed.scheme.lower()
        self._host = parsed.netloc.lower()
        self._path = self._normalize_path(parsed.path)
        self._value = self._assemble_url(
            self._scheme, self._host, self._path, parsed.query, parsed.fragment
        )

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
