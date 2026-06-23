"""Private attribute helpers for run-manifest builder modules."""

from __future__ import annotations

_MISSING = object()


def read_attr(obj: object, attr_name: str, default: object = _MISSING) -> object:
    """Read one attribute with optional fallback semantics."""
    if default is _MISSING:
        return getattr(obj, attr_name)
    return getattr(obj, attr_name, default)
