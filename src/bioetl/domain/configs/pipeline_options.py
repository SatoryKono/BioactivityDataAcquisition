"""Pipeline option configs: profile, transform, normalization.

These are secondary configuration objects used by PipelineConfig.
Small dataclasses consolidated from profile.py, transform.py, normalization.py.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ProfileConfig(BaseModel):
    """Profile configuration on top of pipeline config.

    Represents an execution profile with named overrides that can extend
    other profiles. Used for environment-specific settings (dev, prod, etc.).

    Attributes:
        name: Profile identifier.
        extends: Optional parent profile to inherit from.
        overrides: Dictionary of config overrides to apply.
    """

    name: str
    extends: str | None = None
    overrides: dict[str, object] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


class TransformConfig(BaseModel):
    """Transform stage settings.

    Configuration for the transform stage of the ETL pipeline,
    controlling how data is serialized and processed.

    Attributes:
        serialization_mode: Canonical serialization format for nested fields.
            - "json": Serialize as JSON strings
            - "flat": Flatten nested structures
            - "pipe": Pipe-delimited format
    """

    serialization_mode: Literal["json", "flat", "pipe"] = Field(
        default="json", description="Canonical serialization format for nested fields"
    )

    model_config = ConfigDict(extra="forbid")


class NormalizationConfig(BaseModel):
    """Data normalization configuration.

    Settings for normalizing data during the transform stage,
    including case handling, ID field identification, and custom normalizers.

    Attributes:
        case_sensitive_fields: Fields that should preserve case sensitivity.
        id_fields: Fields containing identifiers.
        custom_normalizers: Mapping of field names to normalizer names.
    """

    case_sensitive_fields: list[str] = Field(default_factory=list)
    id_fields: list[str] = Field(default_factory=list)
    custom_normalizers: dict[str, str] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")


__all__ = ["ProfileConfig", "TransformConfig", "NormalizationConfig"]
