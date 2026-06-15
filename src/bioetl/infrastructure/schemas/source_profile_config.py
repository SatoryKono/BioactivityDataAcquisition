"""Pydantic schema for source-profile extraction policy metadata."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator

from bioetl.domain.models.filter import (
    SourceProfile,
    SourceProfileStatus,
    compute_extraction_params_sha256,
)

_PROFILE_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:[._-][a-z0-9]+)*$")
_SEMVER_PATTERN = re.compile(
    r"^v?(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"
)
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class SourceProfileYamlConfig(BaseModel):
    """Versioned source-side extraction policy metadata."""

    model_config = ConfigDict(extra="forbid")

    profile_id: str = Field(
        default="default",
        description="Stable source-profile identifier for extraction policy.",
    )
    version: str = Field(
        default="1.0.0",
        description="Source-profile version; widening requires a new version.",
    )
    status: SourceProfileStatus = Field(
        default="baseline",
        description="Rollout state for this source-profile policy.",
    )
    extraction_params_sha256: str | None = Field(
        default=None,
        description="SHA256 over canonical filters.extraction_params payload.",
    )
    description: str | None = Field(
        default=None,
        description="Human-readable source-profile scope note.",
    )

    @field_validator("profile_id")
    @classmethod
    def validate_profile_id(cls, value: str) -> str:
        """Normalize and validate source-profile identifiers."""
        normalized = value.strip().lower()
        if not _PROFILE_ID_PATTERN.fullmatch(normalized):
            raise ValueError(
                "source_profile.profile_id must be a lowercase dotted identifier"
            )
        return normalized

    @field_validator("version")
    @classmethod
    def validate_version(cls, value: str) -> str:
        """Normalize source-profile version to numeric semver."""
        normalized = value.strip().lower()
        if normalized.startswith("v"):
            normalized = normalized[1:]
        if not _SEMVER_PATTERN.fullmatch(normalized):
            raise ValueError("source_profile.version must use MAJOR.MINOR.PATCH")
        return normalized

    @field_validator("extraction_params_sha256")
    @classmethod
    def validate_extraction_params_sha256(cls, value: str | None) -> str | None:
        """Validate optional extraction-params hash format."""
        if value is None:
            return None
        normalized = value.strip().lower()
        if normalized.startswith("sha256:"):
            normalized = normalized.split(":", 1)[1]
        if not _SHA256_PATTERN.fullmatch(normalized):
            raise ValueError(
                "source_profile.extraction_params_sha256 must be 64-char SHA256 hex"
            )
        return normalized

    def assert_matches_extraction_params(
        self,
        params: dict[str, str | int | bool],
    ) -> None:
        """Fail if the declared source-profile hash drifts from extraction params."""
        if self.extraction_params_sha256 is None:
            return
        actual = compute_extraction_params_sha256(params)
        if self.extraction_params_sha256 != actual:
            raise ValueError(
                "source_profile.extraction_params_sha256 does not match "
                "filters.extraction_params"
            )

    def to_domain(self) -> SourceProfile:
        """Convert schema object to immutable domain metadata."""
        return SourceProfile(
            profile_id=self.profile_id,
            version=self.version,
            status=self.status,
            extraction_params_sha256=self.extraction_params_sha256,
            description=self.description,
        )


__all__ = ["SourceProfileYamlConfig"]
