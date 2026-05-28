"""Shared configuration merge utilities.

Provides a single deep-merge implementation with pluggable list strategies.
Used by pipeline/source config loading and hierarchical DQ/filter loaders.
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from typing import Any

from bioetl.domain.types import JsonDict

ListMergeFn = Callable[
    [list[Any], list[Any], str],  # Any: heterogeneous YAML values
    list[Any],  # Any: heterogeneous YAML values
]
ListMergeResolver = Callable[[str], ListMergeFn | None]


def _default_concat_list_merger(
    base: list[Any],  # Any: YAML config values are heterogeneous
    override: list[Any],  # Any: YAML config values are heterogeneous
    _key: str,
) -> list[Any]:  # Any: YAML config values are heterogeneous
    """Default list concatenation strategy.

    - String lists: concatenate with deduplication, preserving order.
    - Other lists: plain concatenation.

    Returns:
        Merged list with string deduplication for string lists, or plain concatenation otherwise.
    """
    if all(isinstance(item, str) for item in base) and all(
        isinstance(item, str) for item in override
    ):
        # OPTIMIZATION: dict.fromkeys() leverages fast C-level iteration and
        # insertion-order preservation, outperforming pure-Python seen=set() loops
        return list(dict.fromkeys(base + override))

    return [*base, *override]


def _resolve_list_merger(
    key: str,
    *,
    list_concat_keys: frozenset[str],
    concat_merger: ListMergeFn,
    list_merger_resolver: ListMergeResolver | None,
) -> ListMergeFn | None:
    """Resolve the list merge function for a given key.

    Returns:
        A ListMergeFn if a specific strategy is configured for this key, None for default override.
    """
    if list_merger_resolver is not None:
        resolved = list_merger_resolver(key)
        if resolved is not None:
            return resolved
    if key in list_concat_keys:
        return concat_merger
    return None


def _merge_mapping_value(
    base_value: Mapping[str, Any],  # Any: YAML config values are heterogeneous
    override_value: Mapping[str, Any],  # Any: YAML config values are heterogeneous
    *,
    list_concat_keys: frozenset[str],
    concat_merger: ListMergeFn,
    list_merger_resolver: ListMergeResolver | None,
) -> JsonDict:
    """Recursively merge nested mapping values."""
    return config_merge(
        base_value,
        override_value,
        list_concat_keys=list_concat_keys,
        concat_list_merger=concat_merger,
        list_merger_resolver=list_merger_resolver,
    )


def _merge_list_value(
    key: str,
    base_value: list[Any],  # Any: YAML config values are heterogeneous
    override_value: list[Any],  # Any: YAML config values are heterogeneous
    *,
    list_concat_keys: frozenset[str],
    concat_merger: ListMergeFn,
    list_merger_resolver: ListMergeResolver | None,
) -> list[Any]:  # Any: YAML config values are heterogeneous
    """Merge list values using configured per-key strategy or default override."""
    merger = _resolve_list_merger(
        key,
        list_concat_keys=list_concat_keys,
        concat_merger=concat_merger,
        list_merger_resolver=list_merger_resolver,
    )
    if merger is None:
        return copy.deepcopy(override_value)
    return merger(base_value, override_value, key)


def _merge_config_value(
    key: str,
    base_value: Any,  # Any: YAML config values are heterogeneous
    override_value: Any,  # Any: YAML config values are heterogeneous
    *,
    list_concat_keys: frozenset[str],
    concat_merger: ListMergeFn,
    list_merger_resolver: ListMergeResolver | None,
) -> Any:  # Any: YAML config values are heterogeneous
    """Merge one config value pair using mapping/list/scalar semantics."""
    if isinstance(base_value, dict) and isinstance(override_value, dict):
        return _merge_mapping_value(
            base_value,
            override_value,
            list_concat_keys=list_concat_keys,
            concat_merger=concat_merger,
            list_merger_resolver=list_merger_resolver,
        )

    if isinstance(base_value, list) and isinstance(override_value, list):
        return _merge_list_value(
            key,
            base_value,
            override_value,
            list_concat_keys=list_concat_keys,
            concat_merger=concat_merger,
            list_merger_resolver=list_merger_resolver,
        )

    return copy.deepcopy(override_value)


def config_merge(
    base: Mapping[str, Any],  # Any: YAML config values are heterogeneous
    override: Mapping[str, Any],  # Any: YAML config values are heterogeneous
    *,
    list_concat_keys: frozenset[str] = frozenset(),
    concat_list_merger: ListMergeFn | None = None,
    list_merger_resolver: ListMergeResolver | None = None,
) -> JsonDict:  # Any: YAML config values are heterogeneous
    """Deep-merge two config mappings with optional key-specific list strategies.

    Returns:
        Deep-merged dictionary with override values taking precedence over base values.
    """
    result = copy.deepcopy(dict(base))
    concat_merger = concat_list_merger or _default_concat_list_merger

    for key, override_value in override.items():
        if key not in result:
            result[key] = copy.deepcopy(override_value)
            continue

        result[key] = _merge_config_value(
            key,
            result[key],
            override_value,
            list_concat_keys=list_concat_keys,
            concat_merger=concat_merger,
            list_merger_resolver=list_merger_resolver,
        )

    return result


__all__ = ["ListMergeFn", "ListMergeResolver", "config_merge"]
