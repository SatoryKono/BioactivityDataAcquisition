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
    def _is_filter_enabled(
        yaml_filter: YamlInputFilter, cli_csv: str | None, test_mode: bool
    ) -> bool:
        """Determine if filtering should be enabled."""
        if test_mode:
            return bool(cli_csv)
        return bool(cli_csv) or yaml_filter.enabled

    @staticmethod
    def _build_multi_column_config(
        yaml_filter: YamlInputFilter, effective_csv: str
    ) -> InputFilterConfig:
        """Build config for multi-column filtering mode.

        Caller must ensure yaml_filter.columns is not None.
        """
        assert yaml_filter.columns is not None  # Guaranteed by caller check
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

    @staticmethod
    def _build_single_column_config(
        yaml_filter: YamlInputFilter,
        effective_csv: str,
        cli_column: str | None,
        cli_field: str | None,
        cli_fallback_column: str | None,
    ) -> InputFilterConfig:
        """Build config for single-column filtering mode."""
        effective_column = cli_column or yaml_filter.column_name
        effective_field = cli_field or yaml_filter.filter_field
        effective_fallback = cli_fallback_column or yaml_filter.fallback_column
        return InputFilterConfig(
            enabled=True,
            source_path=effective_csv,
            column_name=effective_column,
            filter_field=effective_field,
            batch_size=yaml_filter.batch_size,
            fallback_column=effective_fallback,
        )

    @staticmethod
    def from_direct_ids(
        filter_ids: tuple[str, ...],
        filter_field: str,
        batch_size: int = 100,
        fallback_mapping: dict[str, str] | None = None,
    ) -> InputFilterConfig:
        """Build config for direct filter IDs mode (no CSV file).

        Used for composite pipelines where IDs are passed programmatically.
        """
        return InputFilterConfig(
            enabled=True,
            filter_field=filter_field,
            direct_filter_ids=filter_ids,
            direct_fallback_mapping=fallback_mapping,
            batch_size=batch_size,
        )

    @staticmethod
    def build(
        yaml_filter: YamlInputFilter,
        cli_csv: str | None = None,
        cli_column: str | None = None,
        cli_field: str | None = None,
        cli_fallback_column: str | None = None,
        *,
        test_mode: bool = False,
        direct_filter_ids: tuple[str, ...] | None = None,
        direct_fallback_mapping: dict[str, str] | None = None,
    ) -> InputFilterConfig | None:
        """Build InputFilterConfig by merging YAML config and CLI overrides.

        Priority:
        1. direct_filter_ids: Direct IDs (highest priority, for composite mode)
        2. cli_csv: CSV path from CLI
        3. yaml_filter: YAML config (disabled in test_mode)

        Multi-column mode (columns list in YAML) is used as-is, CLI overrides ignored.

        Note:
            In test mode, YAML-based filters are disabled to allow E2E tests
            to run without requiring actual filter CSV files.

        Args:
            yaml_filter: Filter configuration from pipeline YAML
            cli_csv: Optional CSV path from CLI (single-column mode only)
            cli_column: Optional column name from CLI (single-column mode only)
            cli_field: Optional filter field from CLI (single-column mode only)
            cli_fallback_column: Optional fallback column from CLI
            test_mode: If True, YAML-based filters are disabled
            direct_filter_ids: Direct filter IDs (no CSV file, for composite mode)
            direct_fallback_mapping: Direct fallback mapping (DOI->Title)

        Returns:
            Configured InputFilterConfig or None if filtering is disabled
        """
        # Direct filter IDs take highest priority (composite mode)
        if direct_filter_ids is not None:
            return FilterConfigBuilder.from_direct_ids(
                filter_ids=direct_filter_ids,
                filter_field=cli_field or yaml_filter.filter_field or "doi",
                batch_size=yaml_filter.batch_size,
                fallback_mapping=direct_fallback_mapping,
            )

        if not FilterConfigBuilder._is_filter_enabled(yaml_filter, cli_csv, test_mode):
            return None

        effective_csv = cli_csv or yaml_filter.source_path
        if not effective_csv:
            return None

        # Multi-column mode: use YAML config as-is
        if yaml_filter.columns and not cli_csv:
            return FilterConfigBuilder._build_multi_column_config(
                yaml_filter, effective_csv
            )

        # Single-column mode: CLI > YAML config
        return FilterConfigBuilder._build_single_column_config(
            yaml_filter, effective_csv, cli_column, cli_field, cli_fallback_column
        )
