"""Profile configuration models (domain layer)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ProfileConfig(BaseModel):
    """Конфигурация профиля поверх пайплайн-конфига."""

    name: str
    extends: str | None = None
    overrides: dict[str, object] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


__all__ = ["ProfileConfig"]
