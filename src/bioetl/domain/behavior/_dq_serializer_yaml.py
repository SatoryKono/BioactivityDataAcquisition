"""Deterministic YAML scalar formatting for DQ report serialization."""

from __future__ import annotations

import re

import orjson

_PLAIN_YAML_STRING = re.compile(r"[A-Za-z_][A-Za-z0-9_.-]*")
_YAML_RESERVED_STRINGS = frozenset(
    {
        "false",
        "n",
        "no",
        "null",
        "off",
        "on",
        "true",
        "y",
        "yes",
        "~",
    }
)


def format_yaml_scalar(value: object) -> str:
    """Return a YAML-safe scalar without coupling Domain to a YAML runtime."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return _format_yaml_string(value)
    return _format_yaml_string(str(value))


def _format_yaml_string(value: str) -> str:
    """Return a deterministic YAML-safe representation of a string scalar."""
    if _PLAIN_YAML_STRING.fullmatch(value) and value.casefold() not in (
        _YAML_RESERVED_STRINGS
    ):
        return value
    encoded = orjson.dumps(value).decode("utf-8")
    return str(encoded)
