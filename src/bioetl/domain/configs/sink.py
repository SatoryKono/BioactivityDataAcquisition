"""Data sink configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class OutputOptionsConfig(BaseModel):
    """Output options for data sink.

    Settings controlling how output data is written.

    Attributes:
        converter: Optional converter name for output transformation.
        format: Output file format (json, parquet, csv).
        compression: Optional compression algorithm (gzip, zstd, none).
    """

    converter: str | None = Field(default=None, description="Output converter name")
    format: Literal["json", "parquet", "csv"] = Field(
        default="json", description="Output file format"
    )
    compression: Literal["gzip", "zstd", "none"] | None = Field(
        default=None, description="Compression algorithm"
    )

    model_config = ConfigDict(frozen=True, extra="forbid")


class DataSinkConfig(BaseModel):
    """Data sink configuration.

    Groups fields related to output: path, dry run mode, output options.
    This is a frozen immutable model for thread-safety and hashability.

    Attributes:
        output_path: Directory or file path for output data.
        dry_run: If True, skip actual data writing (validation only).
        output: Additional output options (format, compression, converter).
    """

    output_path: str = Field(..., description="Output path for data")
    dry_run: bool = Field(default=False, description="Skip actual writing")
    output: OutputOptionsConfig = Field(
        default_factory=OutputOptionsConfig, description="Output options"
    )

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("output_path")
    @classmethod
    def validate_output_path(cls, value: str) -> str:
        """Normalize and validate output path."""
        if not value or not value.strip():
            raise ValueError("output_path must be a non-empty string")
        # Normalize path
        path = Path(value.strip())
        return str(path)

    @field_validator("output_path")
    @classmethod
    def validate_output_path_not_system(cls, value: str) -> str:
        """Prevent writing to dangerous system paths."""
        dangerous_prefixes = ("/etc", "/usr", "/bin", "/sbin", "/boot", "/proc", "/sys")
        for prefix in dangerous_prefixes:
            if value.startswith(prefix):
                raise ValueError(f"output_path cannot start with system path: {prefix}")
        return value


__all__ = ["DataSinkConfig", "OutputOptionsConfig"]
