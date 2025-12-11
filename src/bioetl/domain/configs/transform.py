"""Transform-stage configuration models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TransformConfig(BaseModel):
    """Transform stage settings."""

    serialization_mode: Literal["json", "flat", "pipe"] = Field(
        default="json", description="Canonical serialization format for nested fields"
    )

    model_config = ConfigDict(extra="forbid")


__all__ = ["TransformConfig"]
