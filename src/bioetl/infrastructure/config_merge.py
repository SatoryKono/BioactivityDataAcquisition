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
    if all(isinstance(item, str) for item in base) and all(
        isinstance(item, str) for item in override
    ):
        seen: set[str] = set()
        merged: list[Any] = []
        for item in base + override:
            item_str = str(item)
            if item_str not in seen:
                seen.add(item_str)
                merged.append(item)
        return merged

    return [*base, *override]


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

    Args:
        base: Base.
        override: Override.
        list_concat_keys: List concat keys.
        concat_list_merger: Concat list merger.
        list_merger_resolver: List merger resolver.

    Returns:
        Result dictionary.
    """
    result = copy.deepcopy(dict(base))
    concat_merger = concat_list_merger or _default_concat_list_merger

    for key, override_value in override.items():
        if key not in result:
            result[key] = copy.deepcopy(override_value)
            continue

        base_value = result[key]

        if isinstance(base_value, dict) and isinstance(override_value, dict):
            result[key] = config_merge(
                base_value,
                override_value,
                list_concat_keys=list_concat_keys,
                concat_list_merger=concat_merger,
                list_merger_resolver=list_merger_resolver,
            )
            continue

        if isinstance(base_value, list) and isinstance(override_value, list):
            list_merger: ListMergeFn | None = None

            if list_merger_resolver is not None:
                list_merger = list_merger_resolver(key)

            if list_merger is None and key in list_concat_keys:
                list_merger = concat_merger

            if list_merger is not None:
                result[key] = list_merger(base_value, override_value, key)
            else:
                result[key] = copy.deepcopy(override_value)
            continue

        result[key] = copy.deepcopy(override_value)

    return result


__all__ = ["ListMergeFn", "ListMergeResolver", "config_merge"]
