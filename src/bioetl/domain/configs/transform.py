"""Transform-stage configuration models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TransformConfig(BaseModel):
    """Настройки стадии transform."""

    serialization_mode: Literal["json", "flat", "pipe"] = Field(
        default="json", description="Канонический формат сериализации вложенных полей"
    )

    model_config = ConfigDict(extra="forbid")


__all__ = ["TransformConfig"]
