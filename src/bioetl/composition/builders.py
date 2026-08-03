"""Configuration builders for composition.

Encapsulates logic for constructing configuration objects from multiple sources
(e.g., merging YAML config with CLI arguments).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.filtering import FilterColumn, InputFilterConfig

if TYPE_CHECKING:
    from bioetl.infrastructure.schemas.pipeline_config import (
        InputFilterYamlConfig as YamlInputFilter,
    )


__all__ = [
    "FilterConfigBuilder",
]


class FilterConfigBuilder:
    """Builder for InputFilterConfig."""

    @staticmethod
    def _is_filter_enabled(
        yaml_filter: YamlInputFilter, cli_csv: str | None, test_mode: bool
    ) -> bool:
        """Determine if filtering should be enabled.

        Args:
            yaml_filter: Filter configuration from pipeline YAML.
            cli_csv: CLI-provided CSV path; non-empty value activates filtering.
            test_mode: When True, YAML-based filters are ignored unless a CLI CSV
                is explicitly provided.

        Returns:
            True if input filtering should be applied for this run.
        """
        if test_mode:
            return bool(cli_csv)
        return bool(cli_csv) or yaml_filter.enabled

    @staticmethod
    def _build_multi_column_config(
        yaml_filter: YamlInputFilter, effective_csv: str
    ) -> InputFilterConfig:
        """Build config for multi-column filtering mode.

        Caller must ensure yaml_filter.columns is not None.

        Args:
            yaml_filter: Filter configuration from pipeline YAML providing column specs
                and batch size.
            effective_csv: Resolved path to the CSV file containing filter IDs.

        Returns:
            InputFilterConfig for multi-column filtering mode.
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
        """Build config for single-column filtering mode.

        Args:
            yaml_filter: Filter configuration from pipeline YAML providing defaults.
            effective_csv: Resolved path to the CSV file containing filter IDs.
            cli_column: CLI-provided column name; overrides YAML column if non-None.
            cli_field: CLI-provided API filter field; overrides YAML field if non-None.
            cli_fallback_column: CLI-provided fallback column; overrides YAML if non-None.

        Returns:
            InputFilterConfig for single-column filtering mode.
        """
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

        Args:
            filter_ids: List of identifiers to filter by.
            filter_field: Field name to apply filter on.
            batch_size: Number of records per batch.
            fallback_mapping: Fallback mapping.

        Returns:
            The InputFilterConfig result.
        """
        return InputFilterConfig(
            enabled=True,
            filter_field=filter_field,
            direct_filter_ids=filter_ids,
            direct_fallback_mapping=fallback_mapping,
            batch_size=batch_size,
        )

    @staticmethod
    def from_direct_multi_ids(
        multi_filter_ids: dict[str, tuple[str, ...]],
        valid_combinations: frozenset[tuple[str, ...]] | None = None,
        batch_size: int = 100,
    ) -> InputFilterConfig:
        """Build config for direct multi-field filter IDs mode.

        Used for composite dependencies that filter by multiple fields
        simultaneously (AND logic). E.g., compound_record filtered by both
        molecule_chembl_id and document_chembl_id.

        Args:
            multi_filter_ids: Mapping of field name to tuple of IDs.
            valid_combinations: Valid (field1, field2, ...) tuples for
                client-side combination filtering.
            batch_size: Number of IDs per API request.

        Returns:
            The InputFilterConfig result.
        """
        return InputFilterConfig(
            enabled=True,
            direct_multi_filter_ids=multi_filter_ids,
            direct_valid_combinations=valid_combinations,
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
        direct_multi_filter_ids: dict[str, tuple[str, ...]] | None = None,
        direct_valid_combinations: frozenset[tuple[str, ...]] | None = None,
    ) -> InputFilterConfig | None:
        """Build `InputFilterConfig` from YAML settings and CLI overrides.

        Args:
            yaml_filter: Filter configuration from pipeline YAML providing defaults.
            cli_csv: CLI-provided CSV path override; defaults to None.
            cli_column: CLI-provided column name override; defaults to None.
            cli_field: CLI-provided API filter field override; defaults to None.
            cli_fallback_column: CLI-provided fallback column override; defaults to None.
            test_mode: If True, YAML filters are ignored unless CLI CSV is provided;
                defaults to False.
            direct_filter_ids: Programmatic filter IDs bypassing CSV; defaults to None.
            direct_fallback_mapping: Fallback mapping for direct filter IDs; defaults
                to None.
            direct_multi_filter_ids: Multi-field filter IDs for AND logic; defaults
                to None.
            direct_valid_combinations: Valid combination tuples for client-side
                filtering; defaults to None.

        Returns:
            Configured InputFilterConfig, or None if filtering is disabled.
        """
        if direct_multi_filter_ids is not None:
            return FilterConfigBuilder.from_direct_multi_ids(
                multi_filter_ids=direct_multi_filter_ids,
                valid_combinations=direct_valid_combinations,
                batch_size=yaml_filter.batch_size,
            )

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

        if yaml_filter.columns and not cli_csv:
            return FilterConfigBuilder._build_multi_column_config(
                yaml_filter, effective_csv
            )

        return FilterConfigBuilder._build_single_column_config(
            yaml_filter, effective_csv, cli_column, cli_field, cli_fallback_column
        )
