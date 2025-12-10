"""Data flow configuration - aggregate for source and sink."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, model_validator

from bioetl.domain.configs.sink import DataSinkConfig
from bioetl.domain.configs.source import DataSourceConfig


class DataFlowConfig(BaseModel):
    """Aggregate for data source and destination configuration.

    Groups DataSourceConfig and DataSinkConfig into a single bounded context
    representing the complete data flow: where data comes from and where it goes.

    This aggregate enforces consistency constraints between source and sink,
    such as preventing output to the same file as input.

    Attributes:
        source: Data source configuration (input_mode, input_path, batch_size, csv).
        sink: Data sink configuration (output_path, dry_run, output options).
    """

    source: DataSourceConfig
    sink: DataSinkConfig

    model_config = ConfigDict(frozen=True, extra="forbid")

    @model_validator(mode="after")
    def validate_flow_consistency(self) -> DataFlowConfig:
        """Ensure source and sink are compatible.

        Validates that:
        - Input and output paths don't point to the same file (when applicable)
        - Other cross-cutting constraints between source and sink

        Returns:
            Self if validation passes.

        Raises:
            ValueError: If source and sink configuration is inconsistent.
        """
        # Prevent writing to the same file we're reading from
        if self.source.input_path and self.source.input_mode in ("csv", "id_only"):
            input_path = Path(self.source.input_path).resolve()
            output_path = Path(self.sink.output_path).resolve()

            # Check if output path is the same file as input
            if input_path == output_path:
                raise ValueError(
                    f"Output path cannot be the same as input path: {input_path}"
                )

            # Check if output is inside a directory that is the input file
            # (shouldn't happen, but defensive check)
            try:
                output_path.relative_to(input_path)
                if input_path.is_file():
                    raise ValueError(
                        f"Output path cannot be inside input file path: {input_path}"
                    )
            except ValueError:
                # Not a relative path, which is fine
                pass

        return self


__all__ = ["DataFlowConfig"]
