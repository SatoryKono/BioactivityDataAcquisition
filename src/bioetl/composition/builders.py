"""Configuration builders for composition.

Encapsulates logic for constructing configuration objects from multiple sources
(e.g., merging YAML config with CLI arguments).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.filter_config import InputFilterConfig

if TYPE_CHECKING:
    from bioetl.infrastructure.schemas.pipeline_config import InputFilterConfig as YamlInputFilter


class FilterConfigBuilder:
    """Builder for InputFilterConfig."""

    @staticmethod
    def build(
        yaml_filter: YamlInputFilter,
        cli_csv: str | None = None,
        cli_column: str | None = None,
        cli_field: str | None = None,
    ) -> InputFilterConfig | None:
        """Build InputFilterConfig by merging YAML config and CLI overrides.

        CLI arguments take precedence over YAML configuration.
        Filter is enabled if either:
        1. A CSV path is provided via CLI
        2. The YAML config has enabled=True

        Args:
            yaml_filter: Filter configuration from pipeline YAML
            cli_csv: Optional CSV path from CLI
            cli_column: Optional column name from CLI
            cli_field: Optional filter field from CLI

        Returns:
            Configured InputFilterConfig or None if filtering is disabled
        """
        # Determine effective values: CLI > YAML config
        effective_csv = cli_csv or yaml_filter.source_path
        effective_column = cli_column or yaml_filter.column_name
        effective_field = cli_field or yaml_filter.filter_field

        # Enable filter if: CLI provides --input-csv OR config has enabled=true
        filter_enabled = bool(cli_csv) or yaml_filter.enabled

        if filter_enabled and effective_csv:
            return InputFilterConfig(
                enabled=True,
                source_path=effective_csv,
                column_name=effective_column,
                filter_field=effective_field,
                batch_size=yaml_filter.batch_size,
            )

        return None
