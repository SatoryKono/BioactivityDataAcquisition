"""Typed SCD configuration for Gold contracts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ._gold_contracts_support import normalize_business_key, normalize_column_name

__all__ = ["ScdConfig"]


@dataclass(frozen=True, slots=True)
class ScdConfig:
    """Typed SCD Type 2 configuration used inside the runtime."""

    business_key: str | tuple[str, ...] | None = None
    valid_from_col: str = "valid_from"
    valid_to_col: str = "valid_to"
    current_flag_col: str = "is_current"
    version_col: str = "version"
    scd_type: int = 2

    def __post_init__(self) -> None:
        if self.business_key is not None:
            object.__setattr__(
                self, "business_key", normalize_business_key(self.business_key)
            )
        object.__setattr__(
            self,
            "valid_from_col",
            normalize_column_name(self.valid_from_col, field_name="valid_from_col"),
        )
        object.__setattr__(
            self,
            "valid_to_col",
            normalize_column_name(self.valid_to_col, field_name="valid_to_col"),
        )
        object.__setattr__(
            self,
            "current_flag_col",
            normalize_column_name(self.current_flag_col, field_name="current_flag_col"),
        )
        object.__setattr__(
            self,
            "version_col",
            normalize_column_name(self.version_col, field_name="version_col"),
        )
        if self.scd_type <= 0:
            raise ValueError("scd_type must be positive")

    @property
    def business_keys(self) -> tuple[str, ...]:
        """Return the business key as a normalized tuple."""
        if self.business_key is None:
            return ()
        if isinstance(self.business_key, str):
            return (self.business_key,)
        return self.business_key

    @property
    def entity_key(self) -> str | None:
        """Return single-column entity key when applicable."""
        return self.business_key if isinstance(self.business_key, str) else None

    @classmethod
    def _resolve_business_key(
        cls,
        raw: Mapping[str, object],
        primary_keys: Sequence[str] | None,
    ) -> str | tuple[str, ...] | None:
        business_key = raw.get("business_key", raw.get("entity_key"))
        if business_key is not None:
            return normalize_business_key(business_key)
        if primary_keys:
            return primary_keys[0] if len(primary_keys) == 1 else tuple(primary_keys)
        return None

    @classmethod
    def from_mapping(
        cls,
        raw: Mapping[str, object],
        *,
        primary_keys: Sequence[str] | None = None,
    ) -> ScdConfig:
        """Build typed config from YAML/test mapping input."""
        scd_type_raw = raw.get("type", 2)
        if isinstance(scd_type_raw, bool) or not isinstance(scd_type_raw, int):
            raise ValueError("type must be an integer when provided")

        return cls(
            business_key=cls._resolve_business_key(raw, primary_keys),
            valid_from_col=normalize_column_name(
                raw.get("valid_from_col", raw.get("valid_from", "valid_from")),
                field_name="valid_from_col",
            ),
            valid_to_col=normalize_column_name(
                raw.get("valid_to_col", raw.get("valid_to", "valid_to")),
                field_name="valid_to_col",
            ),
            current_flag_col=normalize_column_name(
                raw.get("current_flag_col", raw.get("is_current", "is_current")),
                field_name="current_flag_col",
            ),
            version_col=normalize_column_name(
                raw.get("version_col", raw.get("version", "version")),
                field_name="version_col",
            ),
            scd_type=scd_type_raw,
        )
