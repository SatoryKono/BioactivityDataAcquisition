"""Normalization configuration for the domain layer."""

from __future__ import annotations

from pydantic import BaseModel, Field


class NormalizationConfig(BaseModel):
    """Data normalization configuration."""

    case_sensitive_fields: list[str] = Field(default_factory=list)
    id_fields: list[str] = Field(default_factory=list)
    custom_normalizers: dict[str, str] = Field(default_factory=dict)

    model_config = {"extra": "forbid"}


__all__ = ["NormalizationConfig"]
