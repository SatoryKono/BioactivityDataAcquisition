"""Configuration builders for composition layer.

Handles merging of configuration from multiple sources (YAML, CLI)
while keeping domain models pure. This module belongs to the composition
layer and is responsible for translating infrastructure configs to domain configs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.filter_config import InputFilterConfig

if TYPE_CHECKING:
    from structlog import BoundLogger

    from bioetl.infrastructure.schemas.pipeline_config import (
        InputFilterConfig as YamlInputFilterConfig,
    )


class FilterConfigBuilder:
    """Builds InputFilterConfig from YAML config and CLI overrides.

    This builder encapsulates the priority logic for merging configuration
    from multiple sources:
    - CLI arguments have highest priority (explicit user intent)
    - YAML config provides defaults

    Example:
        >>> from bioetl.composition.builders import FilterConfigBuilder
        >>> config = FilterConfigBuilder.build(
        ...     yaml_filter=yaml_config.input_filter,
        ...     cli_csv="/path/to/ids.csv",
        ...     cli_column=None,  # Use YAML default
        ...     cli_field=None,
        ...     logger=logger,
        ... )
    """

    @staticmethod
    def build(
        yaml_filter: YamlInputFilterConfig,
        cli_csv: str | None,
        cli_column: str | None,
        cli_field: str | None,
        logger: BoundLogger | None = None,
    ) -> InputFilterConfig | None:
        """Build filter config with CLI overrides.

        Priority: CLI arguments > YAML config values.

        Args:
            yaml_filter: Filter configuration from YAML file.
            cli_csv: CLI --input-csv argument (overrides yaml).
            cli_column: CLI --filter-column argument (overrides yaml).
            cli_field: CLI --filter-field argument (overrides yaml).
            logger: Optional logger for debugging filter configuration.

        Returns:
            InputFilterConfig if filtering is enabled, None otherwise.
            Filtering is enabled if either:
            - CLI provides --input-csv argument, OR
            - YAML config has enabled=true with a valid source_path
        """
        # Determine effective values: CLI > YAML
        effective_csv = cli_csv or yaml_filter.source_path
        effective_column = cli_column or yaml_filter.column_name
        effective_field = cli_field or yaml_filter.filter_field

        # Enable filter if: CLI provides --input-csv OR config has enabled=true
        filter_enabled = bool(cli_csv) or yaml_filter.enabled

        if not filter_enabled or not effective_csv:
            return None

        config = InputFilterConfig(
            enabled=True,
            source_path=effective_csv,
            column_name=effective_column,
            filter_field=effective_field,
            batch_size=yaml_filter.batch_size,
        )

        if logger:
            logger.info(
                "input_filter_enabled",
                csv_path=effective_csv,
                column=effective_column,
                filter_field=effective_field,
                source="cli" if cli_csv else "config",
            )

        return config
