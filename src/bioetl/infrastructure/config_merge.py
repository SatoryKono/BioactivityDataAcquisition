"""Shared configuration merge utilities.

Provides a single deep-merge implementation with pluggable list strategies.
Used by pipeline/source config loading and hierarchical DQ/filter loaders.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from typing import Any

ListMergeFn = Callable[[list[Any], list[Any], str], list[Any]]
ListMergeResolver = Callable[[str], ListMergeFn | None]


def _default_concat_list_merger(
    base: list[Any],
    override: list[Any],
    _key: str,
) -> list[Any]:
    """Default list concatenation strategy.

    - String lists: concatenate with deduplication, preserving order.
    - Other lists: plain concatenation.
    """
    is_str_list = all(isinstance(item, str) for item in base) and all(
        isinstance(item, str) for item in override
    )

    if is_str_list:
        return _merge_str_list(base, override)

    return [*base, *override]


def _merge_str_list(base: list[Any], override: list[Any]) -> list[Any]:
    """Merge string lists with deduplication."""
    seen: set[str] = set()
    merged: list[Any] = []
    for item in base + override:
        item_str = str(item)
        if item_str not in seen:
            seen.add(item_str)
            merged.append(item)
    return merged


def _resolve_list_merger(
    key: str,
    list_concat_keys: frozenset[str],
    concat_merger: ListMergeFn,
    list_merger_resolver: ListMergeResolver | None,
) -> ListMergeFn | None:
    """Resolve the appropriate list merger strategy for a key."""
    if list_merger_resolver:
        merger = list_merger_resolver(key)
        if merger:
            return merger

    if key in list_concat_keys:
        return concat_merger

    return None


def _merge_list_values(
    key: str,
    base: list[Any],
    override: list[Any],
    list_concat_keys: frozenset[str],
    concat_merger: ListMergeFn,
    list_merger_resolver: ListMergeResolver | None,
) -> list[Any]:
    """Merge two list values using resolved strategy."""
    merger = _resolve_list_merger(
        key, list_concat_keys, concat_merger, list_merger_resolver
    )

    if merger:
        return merger(base, override, key)

    return copy.deepcopy(override)


def _merge_dict_values(
    key: str,
    base_value: dict[str, Any],
    override_value: dict[str, Any],
    list_concat_keys: frozenset[str],
    concat_merger: ListMergeFn,
    list_merger_resolver: ListMergeResolver | None,
) -> dict[str, Any]:
    """Recursively merge dictionary values."""
    return config_merge(
        base_value,
        override_value,
        list_concat_keys=list_concat_keys,
        concat_list_merger=concat_merger,
        list_merger_resolver=list_merger_resolver,
    )


def config_merge(
    base: Mapping[str, Any],
    override: Mapping[str, Any],
    *,
    list_concat_keys: frozenset[str] = frozenset(),
    concat_list_merger: ListMergeFn | None = None,
    list_merger_resolver: ListMergeResolver | None = None,
) -> dict[str, Any]:
    """Deep merge two config mappings.

    Rules:
    - Scalars: override wins.
    - Dicts: recursive merge.
    - Lists: strategy-based merge
      1) `list_merger_resolver(key)` if provided and returns merger
      2) `concat_list_merger` when key in `list_concat_keys`
      3) override wins

    Returns a new object; inputs are never mutated.
    """
    result = copy.deepcopy(dict(base))
    concat_merger = concat_list_merger or _default_concat_list_merger

    for key, override_value in override.items():
        if key not in result:
            result[key] = copy.deepcopy(override_value)
            continue

        base_value = result[key]

        if isinstance(base_value, dict) and isinstance(override_value, dict):
            result[key] = _merge_dict_values(
                key,
                base_value,
                override_value,
                list_concat_keys,
                concat_merger,
                list_merger_resolver,
            )
            continue

        if isinstance(base_value, list) and isinstance(override_value, list):
            result[key] = _merge_list_values(
                key,
                base_value,
                override_value,
                list_concat_keys,
                concat_merger,
                list_merger_resolver,
            )
            continue

        result[key] = copy.deepcopy(override_value)

    return result


__all__ = ["ListMergeFn", "ListMergeResolver", "config_merge"]
