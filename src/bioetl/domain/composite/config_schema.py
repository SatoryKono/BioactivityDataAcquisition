"""Column selection configuration models for composite pipelines."""

from __future__ import annotations

from dataclasses import dataclass, field

from .config_merge import ColumnGroupConfig
from .config_validators import (
    coerce_to_tuple,
    coerce_to_typed_tuple,
)

__all__ = ["DataSchemaConfig", "LayerColumnConfig"]


@dataclass(frozen=True, slots=True)
class LayerColumnConfig:
    """Column selection configuration for a single Medallion layer.

    Supports three mutually exclusive selection modes: explicit column list,
    group inclusion, or full column group definitions. Exactly one mode
    may be active; specifying more than one raises ``ValueError``.
    """

    columns: tuple[str, ...] | None = None
    column_groups: tuple[ColumnGroupConfig, ...] | None = None
    include_groups: tuple[str, ...] | None = None
    exclude_fields: tuple[str, ...] | None = None
    rename_fields: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        coerce_to_tuple(self, "columns")
        coerce_to_tuple(self, "include_groups")
        coerce_to_tuple(self, "exclude_fields")
        coerce_to_typed_tuple(self, "column_groups", ColumnGroupConfig)
        if not isinstance(self.rename_fields, dict):
            object.__setattr__(self, "rename_fields", dict(self.rename_fields))
        self._validate()

    def _validate(self) -> None:
        modes = sum(
            [
                self.columns is not None,
                self.include_groups is not None,
                self.column_groups is not None,
            ]
        )
        if modes > 1:
            raise ValueError(
                "LayerColumnConfig: only one of columns/include_groups/column_groups allowed"
            )


@dataclass(frozen=True, slots=True)
class DataSchemaConfig:
    """Top-level schema configuration for composite pipeline column management.

    Defines shared column groups and per-layer (Silver/Gold) column selection
    rules used during the merge phase of composite pipelines.
    """

    column_groups: tuple[ColumnGroupConfig, ...] = ()
    silver: LayerColumnConfig | None = None
    gold: LayerColumnConfig | None = None

    def __post_init__(self) -> None:
        coerce_to_typed_tuple(self, "column_groups", ColumnGroupConfig)
        if isinstance(self.silver, dict):
            object.__setattr__(self, "silver", LayerColumnConfig(**self.silver))
        if isinstance(self.gold, dict):
            object.__setattr__(self, "gold", LayerColumnConfig(**self.gold))

    def get_layer_groups(self, layer: str) -> tuple[ColumnGroupConfig, ...]:
        """Return layer-specific column groups, falling back to top-level groups.

        Args:
            layer: Medallion layer name ('silver' or 'gold').

        Returns:
            Layer-specific column groups if configured, otherwise the top-level groups.
        """
        layer_config: LayerColumnConfig | None = getattr(self, layer, None)
        # ``None`` means fall back to top-level groups; empty tuple means select none.
        if layer_config is not None and layer_config.column_groups is not None:
            return layer_config.column_groups
        return self.column_groups

    def should_include_group(self, layer: str, group_name: str) -> bool:
        """Check whether a column group is included for the given layer.

        Args:
            layer: Medallion layer name ('silver' or 'gold').
            group_name: Name of the column group to check for inclusion.

        Returns:
            True if the group should be included; False if the layer config
            restricts inclusion and the group name is absent.
            ``include_groups is None`` means unrestricted; empty tuple excludes all.
        """
        layer_config = getattr(self, layer, None)
        if layer_config is None or layer_config.include_groups is None:
            return True
        return group_name in layer_config.include_groups
