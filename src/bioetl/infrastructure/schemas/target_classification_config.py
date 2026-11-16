"""Strict YAML boundary for the offline target-classification profile."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, ConfigDict, model_validator

from bioetl.domain.config.target_classification import (
    TargetClassificationConfig,
    TargetClassificationMode,
)


class TargetClassificationYamlConfig(BaseModel):
    """Keep unknown keys and unpinned enabled profiles out of runtime wiring."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    mode: TargetClassificationMode = "off"
    snapshot_manifest: str | None = None
    snapshot_manifest_sha256: str | None = None

    @model_validator(mode="after")
    def validate_profile(self) -> Self:
        self.to_domain()
        return self

    def to_domain(self) -> TargetClassificationConfig:
        return TargetClassificationConfig(
            mode=self.mode,
            snapshot_manifest=self.snapshot_manifest,
            snapshot_manifest_sha256=self.snapshot_manifest_sha256,
        )


__all__ = ["TargetClassificationYamlConfig"]
