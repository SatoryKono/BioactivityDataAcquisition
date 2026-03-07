"""Internal list-merge strategies for DQ validation rules."""

from __future__ import annotations

import copy
from typing import Any, cast

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.config_merge import ListMergeFn


def resolve_list_merger(
    key: str,
    *,
    merge_validation_lists_for_key: ListMergeFn,
) -> ListMergeFn | None:
    """Resolve strategy for list merging in DQ configs."""
    if key.endswith("_validations"):
        return merge_validation_lists_for_key
    return None


def merge_validation_lists_for_key(
    base: list[Any],  # Any: YAML validation items are heterogeneous
    override: list[Any],  # Any: YAML validation items are heterogeneous
    _key: str,
) -> list[Any]:  # Any: YAML validation items are heterogeneous
    """Merge validation lists with deduplication for dict payloads only."""
    if not all(isinstance(item, dict) for item in base) or not all(
        isinstance(item, dict) for item in override
    ):
        return copy.deepcopy(override)

    return merge_validation_lists(
        base=cast(
            list[JsonDict],  # Any: validated dynamic dict payload
            base,  # Any: YAML validation items are heterogeneous
        ),
        override=cast(
            list[JsonDict],  # Any: validated dynamic dict payload
            override,  # Any: YAML validation items are heterogeneous
        ),
    )


def merge_validation_lists(
    base: list[JsonDict],  # Any: YAML DQ config has heterogeneous values
    override: list[JsonDict],  # Any: YAML DQ config has heterogeneous values
) -> list[JsonDict]:  # Any: YAML DQ config has heterogeneous values
    """Merge DQ validation lists while preserving order and replacement rules."""
    result_map: dict[str, JsonDict] = {}  # Any: YAML DQ config has heterogeneous values

    for item in base:
        result_map[_validation_key(item)] = copy.deepcopy(item)
    for item in override:
        result_map[_validation_key(item)] = copy.deepcopy(item)

    return list(result_map.values())


def _validation_key(
    item: JsonDict,  # Any: YAML DQ config has heterogeneous values
) -> str:
    """Build stable key for validation deduplication."""
    if "name" in item:
        return str(item["name"])
    field = item.get("field", "")
    validation_type = item.get("type", "")
    severity = item.get("severity", "error")
    return f"{field}:{validation_type}:{severity}"
