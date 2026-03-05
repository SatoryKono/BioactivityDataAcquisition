"""YAML loader for field group configuration.

Loads and validates field group definitions from YAML files,
converting them to domain objects (FieldGroupRegistry).

See ADR-026 for Composite Publication Pipeline rationale.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from bioetl.domain.composite.field_groups import (
    DEFAULT_PROVIDER_ORDER,
    FieldGroupDefinition,
    FieldGroupId,
    FieldGroupRegistry,
    FieldMapping,
    build_field_group_registry,
)
from bioetl.domain.types import JsonDict

__all__ = [
    "FieldGroupLoadError",
    "load_field_groups",
]


class FieldGroupLoadError(ValueError):
    """Error loading field group configuration."""


def load_field_groups(path: Path) -> FieldGroupRegistry:
    """Load field group configuration from YAML file.

    Parses the YAML file, validates structure, and converts to
    domain objects (FieldGroupRegistry).

    Args:
        path: Path to the YAML configuration file.

    Returns:
        Configured FieldGroupRegistry instance.

    Raises:
        FileNotFoundError: If the config file doesn't exist.
        FieldGroupLoadError: If the config is invalid.
    """
    if not path.exists():
        raise FileNotFoundError(f"Field group config not found: {path}")

    with path.open(encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise FieldGroupLoadError(
            f"Invalid field group config: expected dict, got {type(raw).__name__}"
        )

    return _parse_config(raw, source=str(path))


def _parse_config(
    raw: JsonDict,  # Any: YAML config has heterogeneous values
    source: str,  # Any: YAML config has heterogeneous values
) -> FieldGroupRegistry:  # Any: YAML config has heterogeneous values
    """Parse raw YAML dict into FieldGroupRegistry.

    Args:
        raw: Parsed YAML content.
        source: Source path for error messages.

    Returns:
        Configured FieldGroupRegistry.

    Raises:
        FieldGroupLoadError: If validation fails.
    """
    # Parse provider order
    provider_order = tuple(raw.get("provider_order", DEFAULT_PROVIDER_ORDER))

    # Parse groups
    raw_groups = raw.get("groups", [])
    if not isinstance(raw_groups, list):
        raise FieldGroupLoadError(
            f"Invalid 'groups' in {source}: expected list, got {type(raw_groups).__name__}"
        )

    groups: list[FieldGroupDefinition] = []
    for i, raw_group in enumerate(raw_groups):
        try:
            group_def = _parse_group(raw_group, i)
            groups.append(group_def)
        except (KeyError, ValueError, TypeError) as e:
            raise FieldGroupLoadError(
                f"Invalid group at index {i} in {source}: {e}"
            ) from e

    return build_field_group_registry(
        groups=tuple(groups),
        provider_order=provider_order,
    )


def _parse_group(
    raw_group: JsonDict,  # Any: YAML config has heterogeneous values
    index: int,  # Any: YAML config has heterogeneous values
) -> FieldGroupDefinition:  # Any: YAML config has heterogeneous values
    """Parse a single group definition from YAML.

    Args:
        raw_group: Raw group dict from YAML.
        index: Group index for error messages.

    Returns:
        FieldGroupDefinition instance.

    Raises:
        KeyError: If required fields are missing.
        ValueError: If group ID is invalid.
    """
    group_id_str = raw_group.get("id")
    if not group_id_str:
        raise KeyError(f"Group at index {index} missing 'id'")

    group_id = FieldGroupId.from_string(group_id_str)
    display_name = raw_group.get("display_name", group_id.display_name)
    include_in_gold = raw_group.get("include_in_gold", group_id.include_in_gold)

    raw_fields = raw_group.get("fields", [])
    fields: list[FieldMapping] = []

    for j, raw_field in enumerate(raw_fields):
        try:
            field_mapping = _parse_field(raw_field, group_id)
            fields.append(field_mapping)
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(
                f"Invalid field at index {j} in group '{group_id_str}': {e}"
            ) from e

    return FieldGroupDefinition(
        group_id=group_id,
        display_name=display_name,
        include_in_gold=include_in_gold,
        fields=tuple(fields),
    )


def _parse_field(
    raw_field: JsonDict,  # Any: YAML config has heterogeneous values
    group_id: FieldGroupId,  # Any: YAML config has heterogeneous values
) -> FieldMapping:  # Any: YAML config has heterogeneous values
    """Parse a single field mapping from YAML.

    Args:
        raw_field: Raw field dict from YAML.
        group_id: Parent group ID.

    Returns:
        FieldMapping instance.

    Raises:
        KeyError: If required fields are missing.
    """
    base_name = raw_field.get("base_name")
    if not base_name:
        raise KeyError("Field missing 'base_name'")

    columns = raw_field.get("columns", [])
    if not isinstance(columns, list):
        raise TypeError(f"'columns' must be a list, got {type(columns).__name__}")

    return FieldMapping(
        base_name=base_name,
        provider_columns=tuple(columns),
        group=group_id,
    )
