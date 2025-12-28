"""Tests for domain/config_types.py TypedDict definitions.

These tests verify that TypedDict structures correctly type-check
and can be instantiated with valid configuration data.
"""

from __future__ import annotations


from bioetl.domain.config_types import (
    BronzeSinkDict,
    CircuitBreakerDict,
    ClientConfigDict,
    CsvExportDict,
    DQRulesDict,
    GoldFiltersDict,
    GoldRangeDict,
    GoldSinkDict,
    InputFilterDict,
    PipelineConfigDict,
    ProviderConfigDict,
    RateLimitDict,
    RuntimeArgsDict,
    SilverSinkDict,
    SinkDict,
    SourceConfigDict,
    SourceFileDict,
    TransformDict,
)


class TestGoldRangeDict:
    """Tests for GoldRangeDict TypedDict."""

    def test_empty_range(self) -> None:
        """GoldRangeDict can be empty (total=False)."""
        range_dict: GoldRangeDict = {}
        assert isinstance(range_dict, dict)

    def test_full_range(self) -> None:
        """GoldRangeDict with all fields."""
        range_dict: GoldRangeDict = {
            "min": 0.0,
            "max": 100.0,
            "include_min": True,
            "include_max": False,
        }
        assert range_dict["min"] == 0.0
        assert range_dict["max"] == 100.0
        assert range_dict["include_min"] is True
        assert range_dict["include_max"] is False

    def test_partial_range(self) -> None:
        """GoldRangeDict with only min."""
        range_dict: GoldRangeDict = {"min": 5.0}
        assert range_dict["min"] == 5.0


class TestGoldFiltersDict:
    """Tests for GoldFiltersDict TypedDict."""

    def test_empty_filters(self) -> None:
        """GoldFiltersDict can be empty."""
        filters: GoldFiltersDict = {}
        assert isinstance(filters, dict)

    def test_column_filters(self) -> None:
        """GoldFiltersDict with column filters."""
        filters: GoldFiltersDict = {
            "columns": {
                "standard_type": ["IC50", "Ki"],
                "target_type": ["SINGLE PROTEIN"],
            }
        }
        assert "IC50" in filters["columns"]["standard_type"]

    def test_range_filters(self) -> None:
        """GoldFiltersDict with range filters."""
        filters: GoldFiltersDict = {
            "ranges": {
                "standard_value": {"min": 0.0, "max": 1000.0},
            }
        }
        assert filters["ranges"]["standard_value"]["max"] == 1000.0

    def test_required_fields(self) -> None:
        """GoldFiltersDict with required_fields."""
        filters: GoldFiltersDict = {
            "required_fields": ["molecule_id", "target_id"],
        }
        assert "molecule_id" in filters["required_fields"]

    def test_list_filters(self) -> None:
        """GoldFiltersDict with list_length and list_contains."""
        filters: GoldFiltersDict = {
            "list_length": {"synonyms": {"min_length": 1, "max_length": 10}},
            "list_contains": {"types": {"values": ["protein"], "mode": "any"}},
        }
        assert filters["list_length"]["synonyms"]["min_length"] == 1


class TestCsvExportDict:
    """Tests for CsvExportDict TypedDict."""

    def test_full_csv_config(self) -> None:
        """CsvExportDict with all fields."""
        config: CsvExportDict = {
            "enabled": True,
            "path": "/data/exports/output.csv",
            "delimiter": ",",
            "header": True,
            "encoding": "utf-8",
        }
        assert config["enabled"] is True
        assert config["delimiter"] == ","


class TestBronzeSinkDict:
    """Tests for BronzeSinkDict TypedDict."""

    def test_bronze_sink_config(self) -> None:
        """BronzeSinkDict configuration."""
        config: BronzeSinkDict = {
            "path": "data/bronze",
            "format": "jsonl",
            "save_json": True,
        }
        assert config["format"] == "jsonl"


class TestSilverSinkDict:
    """Tests for SilverSinkDict TypedDict."""

    def test_silver_sink_full(self) -> None:
        """SilverSinkDict with all fields."""
        config: SilverSinkDict = {
            "path": "data/silver",
            "format": "delta",
            "mode": "merge",
            "primary_key": ["activity_id"],
            "partition_by": ["year"],
            "classification": "internal",
            "forensic_retention": True,
            "csv_export": {"enabled": False},
        }
        assert config["mode"] == "merge"
        assert config["primary_key"] == ["activity_id"]


class TestGoldSinkDict:
    """Tests for GoldSinkDict TypedDict."""

    def test_gold_sink_config(self) -> None:
        """GoldSinkDict configuration."""
        config: GoldSinkDict = {
            "enabled": True,
            "validation": {"strict": True},
            "path": "data/gold",
            "format": "delta",
            "mode": "scd2",
        }
        assert config["mode"] == "scd2"


class TestSinkDict:
    """Tests for SinkDict TypedDict."""

    def test_complete_sink(self) -> None:
        """SinkDict with all layers."""
        config: SinkDict = {
            "bronze": {"path": "data/bronze", "format": "jsonl"},
            "silver": {"path": "data/silver", "format": "delta"},
            "gold": {"enabled": True, "path": "data/gold"},
        }
        assert "bronze" in config
        assert "silver" in config
        assert "gold" in config


class TestTransformDict:
    """Tests for TransformDict TypedDict."""

    def test_transform_config(self) -> None:
        """TransformDict configuration."""
        config: TransformDict = {
            "version": "1.0.0",
            "steps": ["normalize", "validate", "enrich"],
        }
        assert "normalize" in config["steps"]


class TestDQRulesDict:
    """Tests for DQRulesDict TypedDict."""

    def test_dq_rules_config(self) -> None:
        """DQRulesDict with thresholds."""
        config: DQRulesDict = {
            "soft_fail_threshold": 0.05,
            "hard_fail_threshold": 0.20,
            "strict_validation": True,
        }
        assert config["soft_fail_threshold"] == 0.05
        assert config["hard_fail_threshold"] == 0.20


class TestCircuitBreakerDict:
    """Tests for CircuitBreakerDict TypedDict."""

    def test_circuit_breaker_config(self) -> None:
        """CircuitBreakerDict configuration."""
        config: CircuitBreakerDict = {
            "failure_threshold": 5,
            "recovery_timeout": 300,
        }
        assert config["failure_threshold"] == 5


class TestInputFilterDict:
    """Tests for InputFilterDict TypedDict."""

    def test_input_filter_config(self) -> None:
        """InputFilterDict configuration."""
        config: InputFilterDict = {
            "enabled": True,
            "source_path": "data/filters/molecules.csv",
            "column_name": "chembl_id",
            "filter_field": "molecule_chembl_id",
            "batch_size": 100,
        }
        assert config["enabled"] is True
        assert config["batch_size"] == 100


class TestClientConfigDict:
    """Tests for ClientConfigDict TypedDict."""

    def test_client_config(self) -> None:
        """ClientConfigDict configuration."""
        config: ClientConfigDict = {
            "timeout_sec": 30.0,
            "max_retries": 3,
        }
        assert config["timeout_sec"] == 30.0


class TestRateLimitDict:
    """Tests for RateLimitDict TypedDict."""

    def test_rate_limit_config(self) -> None:
        """RateLimitDict configuration."""
        config: RateLimitDict = {
            "requests_per_second": 10,
            "burst": 20,
        }
        assert config["requests_per_second"] == 10


class TestProviderConfigDict:
    """Tests for ProviderConfigDict TypedDict."""

    def test_provider_config(self) -> None:
        """ProviderConfigDict configuration."""
        config: ProviderConfigDict = {
            "provider": "chembl",
            "base_url": "https://www.ebi.ac.uk/chembl/api/data",
            "client": {"timeout_sec": 30.0},
            "max_url_length": 2048,
            "batch_size": 100,
            "page_size": 1000,
            "api_version": "v1",
        }
        assert config["provider"] == "chembl"


class TestSourceConfigDict:
    """Tests for SourceConfigDict TypedDict."""

    def test_source_config(self) -> None:
        """SourceConfigDict configuration."""
        config: SourceConfigDict = {
            "type": "api",
            "load_strategy": "incremental",
            "batch_size": 500,
            "provider_config": {"provider": "chembl"},
            "circuit_breaker": {"failure_threshold": 5},
            "rate_limit": {"requests_per_second": 10},
        }
        assert config["type"] == "api"
        assert config["load_strategy"] == "incremental"


class TestSourceFileDict:
    """Tests for SourceFileDict TypedDict."""

    def test_source_file_dict(self) -> None:
        """SourceFileDict configuration."""
        config: SourceFileDict = {
            "source": {
                "type": "api",
                "batch_size": 100,
            }
        }
        assert config["source"]["type"] == "api"


class TestPipelineConfigDict:
    """Tests for PipelineConfigDict TypedDict."""

    def test_minimal_pipeline_config(self) -> None:
        """PipelineConfigDict with required fields only."""
        config: PipelineConfigDict = {
            "pipeline_name": "chembl_activity",
            "provider": "chembl",
            "entity_type": "activity",
        }
        assert config["pipeline_name"] == "chembl_activity"

    def test_full_pipeline_config(self) -> None:
        """PipelineConfigDict with all fields."""
        config: PipelineConfigDict = {
            "pipeline_name": "chembl_activity",
            "provider": "chembl",
            "entity_type": "activity",
            "version": "1.0.0",
            "description": "ChEMBL Activity Pipeline",
            "primary_keys": ["activity_id"],
            "silver_table": "chembl_activity_silver",
            "gold_table": "chembl_activity_gold",
            "source_file": "chembl.yaml",
            "gold_filters": {"columns": {"standard_type": ["IC50"]}},
            "input_filter": {"enabled": False},
            "transform": {"version": "1.0"},
            "sink": {"bronze": {"path": "data/bronze"}},
            "dq_rules": {"soft_fail_threshold": 0.05},
            "circuit_breaker": {"failure_threshold": 5},
        }
        assert config["version"] == "1.0.0"
        assert config["primary_keys"] == ["activity_id"]


class TestRuntimeArgsDict:
    """Tests for RuntimeArgsDict TypedDict."""

    def test_runtime_args_config(self) -> None:
        """RuntimeArgsDict with CLI arguments."""
        config: RuntimeArgsDict = {
            "run_type": "incremental",
            "limit": 1000,
            "query": "target_id:CHEMBL123",
            "resume": True,
            "dry_run": False,
            "wait_for_lock": True,
            "lock_wait_timeout": 300,
            "heartbeat_interval": 30,
            "vacuum_after_run": True,
            "vacuum_retention_days": 7,
            "strict_validation": True,
            "strict_gold_validation": False,
            "input_csv": "filters.csv",
            "filter_column": "molecule_id",
            "filter_field": "molecule_chembl_id",
        }
        assert config["run_type"] == "incremental"
        assert config["limit"] == 1000

    def test_empty_runtime_args(self) -> None:
        """RuntimeArgsDict can be empty."""
        config: RuntimeArgsDict = {}
        assert isinstance(config, dict)


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports_importable(self) -> None:
        """All items in __all__ are importable."""
        from bioetl.domain import config_types

        for name in config_types.__all__:
            assert hasattr(config_types, name), f"{name} not found in module"

    def test_expected_exports_count(self) -> None:
        """Expected number of exports."""
        from bioetl.domain import config_types

        # Verify we have the expected TypedDicts
        expected_count = 20  # 20 TypedDicts defined in config_types.py
        assert len(config_types.__all__) == expected_count
