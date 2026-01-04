"""Configuration builders for composition.

Encapsulates logic for constructing configuration objects from multiple sources
(e.g., merging YAML config with CLI arguments).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.filtering import FilterColumn, InputFilterConfig

if TYPE_CHECKING:
    from bioetl.infrastructure.schemas.pipeline_config import (
        InputFilterConfig as YamlInputFilter,
    )


class FilterConfigBuilder:
    """Builder for InputFilterConfig."""

    @staticmethod
    def build(
        yaml_filter: YamlInputFilter,
        cli_csv: str | None = None,
        cli_column: str | None = None,
        cli_field: str | None = None,
        *,
        test_mode: bool = False,
    ) -> InputFilterConfig | None:
        """Build InputFilterConfig by merging YAML config and CLI overrides.

        CLI arguments take precedence over YAML configuration for single-column mode.
        Filter is enabled if either:
        1. A CSV path is provided via CLI
        2. The YAML config has enabled=True (ignored in test mode)

        Multi-column mode (columns list in YAML) is used as-is, CLI overrides ignored.

        Note:
            In test mode, YAML-based filters are disabled to allow E2E tests
            to run without requiring actual filter CSV files. Only explicitly
            provided CLI filters will be used in test mode.

        Args:
            yaml_filter: Filter configuration from pipeline YAML
            cli_csv: Optional CSV path from CLI (single-column mode only)
            cli_column: Optional column name from CLI (single-column mode only)
            cli_field: Optional filter field from CLI (single-column mode only)
            test_mode: If True, YAML-based filters are disabled (from Settings.test_mode)

        Returns:
            Configured InputFilterConfig or None if filtering is disabled
        """
        # In test mode, only enable filter if CLI explicitly provides --input-csv
        # This allows E2E tests to run without actual filter CSV files
        if test_mode:
            filter_enabled = bool(cli_csv)
        else:
            # Enable filter if: CLI provides --input-csv OR config has enabled=true
            filter_enabled = bool(cli_csv) or yaml_filter.enabled

        if not filter_enabled:
            return None

        # Determine effective CSV path
        effective_csv = cli_csv or yaml_filter.source_path
        if not effective_csv:
            return None

        # Check for multi-column mode (columns list in YAML)
        if yaml_filter.columns and not cli_csv:
            # Multi-column mode: use YAML config as-is
            domain_columns = tuple(
                FilterColumn(
                    column_name=col.column_name,
                    filter_field=col.filter_field,
                )
                for col in yaml_filter.columns
            )
            return InputFilterConfig(
                enabled=True,
                source_path=effective_csv,
                columns=domain_columns,
                batch_size=yaml_filter.batch_size,
            )

        # Single-column mode: CLI > YAML config
        effective_column = cli_column or yaml_filter.column_name
        effective_field = cli_field or yaml_filter.filter_field

        return InputFilterConfig(
            enabled=True,
            source_path=effective_csv,
            column_name=effective_column,
            filter_field=effective_field,
            batch_size=yaml_filter.batch_size,
        )
