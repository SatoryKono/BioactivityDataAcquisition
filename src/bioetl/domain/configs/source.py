"""Data source configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PositiveInt,
    field_validator,
    model_validator,
)


class CsvInputConfig(BaseModel):
    """CSV input configuration.

    Settings for parsing CSV input files.

    Attributes:
        delimiter: Field delimiter character.
        header: Whether the CSV has a header row.
        encoding: File encoding (default: utf-8).
        quote_char: Character used for quoting fields.
    """

    delimiter: str = Field(default=",", description="Field delimiter")
    header: bool = Field(default=True, description="CSV has header row")
    encoding: str = Field(default="utf-8", description="File encoding")
    quote_char: str = Field(default='"', description="Quote character")

    model_config = ConfigDict(frozen=True, extra="forbid")

    @field_validator("delimiter")
    @classmethod
    def validate_delimiter(cls, value: str) -> str:
        """Validate that CSV delimiter is a non-empty string."""
        if not value:
            raise ValueError("CSV delimiter must be a non-empty string")
        return value

    @field_validator("encoding")
    @classmethod
    def validate_encoding(cls, value: str) -> str:
        """Validate encoding is a known codec."""
        import codecs

        try:
            codecs.lookup(value)
        except LookupError as err:
            raise ValueError(f"Unknown encoding: {value}") from err
        return value


class DataSourceConfig(BaseModel):
    """Data source configuration.

    Groups fields related to input data: mode, path, batching, CSV options.
    This is a frozen immutable model for thread-safety and hashability.

    Attributes:
        input_mode: How to read input data (csv, id_only, auto_detect).
        input_path: Path to input file (required for csv/id_only modes).
        batch_size: Number of records to process per batch.
        csv: CSV parsing options.
    """

    input_mode: Literal["csv", "id_only", "auto_detect"] = Field(
        ..., description="Input reading mode"
    )
    input_path: str | None = Field(default=None, description="Path to input file")
    batch_size: PositiveInt = Field(default=100, description="Records per batch")
    csv: CsvInputConfig = Field(
        default_factory=CsvInputConfig,
        alias="csv_options",
        description="CSV parsing options",
    )

    model_config = ConfigDict(frozen=True, extra="forbid", populate_by_name=True)

    @field_validator("input_path")
    @classmethod
    def validate_input_path(cls, value: str | None) -> str | None:
        """Normalize empty input path to None and ensure path string."""
        if value is None or value == "":
            return None
        path = Path(value)
        return str(path)

    @model_validator(mode="after")
    def validate_input_mode_requires_path(self) -> DataSourceConfig:
        """Validate that csv/id_only modes require input_path."""
        if self.input_mode in {"csv", "id_only"} and not self.input_path:
            raise ValueError(
                f"input_path must be provided when input_mode is '{self.input_mode}'"
            )
        return self

    @model_validator(mode="after")
    def validate_csv_header_required(self) -> DataSourceConfig:
        """Validate CSV header requirement for csv and auto_detect modes."""
        if self.input_mode == "csv" and not self.csv.header:
            raise ValueError("csv.header must be true when input_mode is 'csv'")

        if self.input_mode == "auto_detect" and self.input_path and not self.csv.header:
            raise ValueError(
                "csv.header must be true when input_mode is 'auto_detect' "
                "and input_path is set"
            )
        return self


__all__ = ["CsvInputConfig", "DataSourceConfig"]
