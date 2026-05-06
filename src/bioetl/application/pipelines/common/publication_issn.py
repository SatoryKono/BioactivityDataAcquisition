"""Shared ISSN helpers for publication provider transformers."""

from __future__ import annotations

from collections.abc import Callable, Sequence


def _normalize_issn_input(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return value.split(",") if "," in value else [value]
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [str(item) for item in value if item is not None]
    return [str(value)]


def _finalize_issn_fields(
    values: list[str],
    *,
    serialize_json_list: Callable[[Sequence[object] | None], str | None],
) -> dict[str, str | None]:
    issn_values = [item.strip() for item in values if item and item.strip()]
    return {
        "issn": issn_values[0] if issn_values else None,
        "issn_list": serialize_json_list(issn_values) if issn_values else None,
    }


def build_issn_fields(
    value: object,
    *,
    serialize_json_list: Callable[[Sequence[object] | None], str | None],
) -> dict[str, str | None]:
    """Return unified scalar and JSON-array ISSN fields.

    Provider APIs expose ISSNs as scalars, comma-delimited strings, or lists.
    Silver/Gold contracts keep a primary scalar `issn` plus `issn_list` for
    deterministic cross-provider merge behavior.
    """
    return _finalize_issn_fields(
        _normalize_issn_input(value),
        serialize_json_list=serialize_json_list,
    )


__all__ = ["build_issn_fields"]
