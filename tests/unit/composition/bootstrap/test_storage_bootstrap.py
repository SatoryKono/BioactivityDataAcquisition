"""Tests for storage bootstrap functions.

Tests the bootstrap functions for storage components used by CLI operations.
"""

from __future__ import annotations

from tests.helpers.synthetic_paths import synthetic_test_root
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from bioetl.application.services.lineage import MetadataCoordinator
from bioetl.composition.bootstrap.cli.storage import (
    _create_cli_preview_run_context,
    _create_table_collector,
    bootstrap_cli_storage_adapter,
    bootstrap_bronze_cleanup_service,
    bootstrap_cleanup_service,
    bootstrap_lifecycle_service,
    bootstrap_vacuum_service,
)
from bioetl.composition.factories.storage import StorageBundle
from bioetl.composition.registry_api import PipelineRegistry
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.observability.noop_logger import NoOpLogger
from bioetl.infrastructure.time import SystemClock

TEST_ROOT = synthetic_test_root("bioetl-storage-bootstrap")
BRONZE_PATH = TEST_ROOT / "bronze"
SILVER_PATH = TEST_ROOT / "silver"
GOLD_PATH = TEST_ROOT / "gold"


def _registry_with_pipelines(*pipeline_names: str) -> MagicMock:
    """Create an explicit registry double for table-collector tests."""
    registry = MagicMock(spec=PipelineRegistry)
    registry.list_pipelines.return_value = list(pipeline_names)
    return registry


def _make_storage_settings(tmp_path: Path) -> SimpleNamespace:
    """Create the minimal settings object required by storage bootstrap."""
    return SimpleNamespace(
        data_dir=str(tmp_path),
        pipeline=SimpleNamespace(silver_resilience_enabled=False),
    )


@pytest.mark.unit
class TestBootstrapStorageBundle:
    """Test bootstrap_storage_adapter function."""

    def test_preview_run_context_is_timestamp_seeded_but_uuid_shaped(self) -> None:
        """Preview storage context should use a stable deterministic UUID seed."""
        first = _create_cli_preview_run_context()
        second = _create_cli_preview_run_context()

        assert UUID(str(first.run_id))
        assert first.run_id != second.run_id

    @patch("bioetl.composition.bootstrap.assembly.storage.get_settings")
    def test_returns_storage_adapter(self, mock_settings: MagicMock) -> None:
        """Test that bootstrap_storage_adapter returns a StorageBundle."""
        mock_settings.return_value.bronze_path = str(BRONZE_PATH)
        mock_settings.return_value.silver_path = str(SILVER_PATH)
        mock_settings.return_value.gold_path = str(GOLD_PATH)

        result = bootstrap_cli_storage_adapter()

        assert isinstance(result, StorageBundle)

    @patch("bioetl.composition.bootstrap.assembly.storage.get_settings")
    def test_wires_output_paths_and_noop_loggers(
        self,
        mock_settings: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Bootstrap should wire writers to data/output with NoOp loggers."""
        mock_settings.return_value = _make_storage_settings(tmp_path)

        result = bootstrap_cli_storage_adapter()
        output_root = tmp_path / "output"

        assert result.bronze.base_path == output_root / "bronze"
        assert Path(result.silver.base_path) == output_root / "silver"
        assert Path(result.gold.base_path) == output_root / "gold"
        assert isinstance(result.bronze._logger, NoOpLogger)
        assert isinstance(result.silver.logger, NoOpLogger)
        assert isinstance(result.gold.logger, NoOpLogger)

    @patch("bioetl.composition.bootstrap.assembly.storage.get_settings")
    def test_disables_csv_export_by_default(
        self,
        mock_settings: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Bootstrap should not wire CSV exporters unless explicitly enabled."""
        mock_settings.return_value = _make_storage_settings(tmp_path)

        result = bootstrap_cli_storage_adapter()

        assert result.silver.csv_exporter is None
        assert result.gold.csv_exporter is None

    @patch("bioetl.composition.bootstrap.assembly.storage.get_settings")
    def test_enables_csv_export_and_shares_composite_metadata_context(
        self,
        mock_settings: MagicMock,
        tmp_path: Path,
    ) -> None:
        """CSV-enabled bootstrap should wire exporters and shared metadata context."""
        mock_settings.return_value = _make_storage_settings(tmp_path)

        result = bootstrap_cli_storage_adapter(enable_csv_export=True)
        output_root = tmp_path / "output"
        metadata_coordinator = result.silver._metadata_coordinator

        assert isinstance(result.silver.csv_exporter, CsvExporter)
        assert isinstance(result.gold.csv_exporter, CsvExporter)
        assert result.silver.csv_exporter.base_path == output_root / "silver"
        assert result.gold.csv_exporter.base_path == output_root / "gold"
        assert isinstance(metadata_coordinator, MetadataCoordinator)
        assert metadata_coordinator is result.gold._metadata_coordinator
        assert result.silver._metadata_writer is result.gold._metadata_writer
        assert metadata_coordinator.run_context.pipeline_name == "cli-storage-preview"
        assert metadata_coordinator.run_context.provider == "cli"
        assert metadata_coordinator.run_context.entity == "maintenance"


@pytest.mark.unit
class TestBootstrapCleanupService:
    """Test bootstrap_cleanup_service function."""

    @patch("bioetl.composition.bootstrap.assembly.storage.get_settings")
    def test_returns_cleanup_service(self, mock_settings: MagicMock) -> None:
        """Test that bootstrap_cleanup_service returns a CleanupService."""
        mock_settings.return_value.bronze_path = str(BRONZE_PATH)
        mock_settings.return_value.silver_path = str(SILVER_PATH)
        mock_settings.return_value.gold_path = str(GOLD_PATH)

        result = bootstrap_cleanup_service()

        from bioetl.application.core.lifecycle.cleanup_service import CleanupService

        assert isinstance(result, CleanupService)


@pytest.mark.unit
class TestBootstrapLifecycleService:
    """Test bootstrap_lifecycle_service function."""

    @patch("bioetl.composition.bootstrap.assembly.storage.get_settings")
    def test_returns_medallion_lifecycle_service(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test that bootstrap_lifecycle_service returns MedallionLifecycleService."""
        mock_settings.return_value.bronze_path = str(BRONZE_PATH)
        mock_settings.return_value.silver_path = str(SILVER_PATH)
        mock_settings.return_value.gold_path = str(GOLD_PATH)

        result = bootstrap_lifecycle_service()

        from bioetl.application.services.medallion_lifecycle import (
            MedallionLifecycleService,
        )

        assert isinstance(result, MedallionLifecycleService)


@pytest.mark.unit
class TestBootstrapBronzeCleanupService:
    """Test bootstrap_bronze_cleanup_service function."""

    @patch("bioetl.composition.bootstrap.assembly.storage.get_settings")
    def test_returns_bronze_cleanup_service(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test that bootstrap_bronze_cleanup_service returns BronzeCleanupService."""
        mock_settings.return_value.bronze_path = str(BRONZE_PATH)
        mock_settings.return_value.silver_path = str(SILVER_PATH)
        mock_settings.return_value.gold_path = str(GOLD_PATH)

        result = bootstrap_bronze_cleanup_service()

        from bioetl.application.services.bronze_cleanup_service import (
            BronzeCleanupService,
        )

        assert isinstance(result, BronzeCleanupService)

    @patch("bioetl.composition.bootstrap.assembly.storage.get_settings")
    def test_wires_system_clock(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Bronze cleanup bootstrap must wire the canonical clock adapter."""
        mock_settings.return_value.bronze_path = str(BRONZE_PATH)
        mock_settings.return_value.silver_path = str(SILVER_PATH)
        mock_settings.return_value.gold_path = str(GOLD_PATH)

        result = bootstrap_bronze_cleanup_service()

        assert isinstance(result.clock, SystemClock)


@pytest.mark.unit
class TestBootstrapVacuumService:
    """Test bootstrap_vacuum_service function."""

    @patch("bioetl.composition.bootstrap.assembly.storage.get_settings")
    def test_returns_vacuum_service(self, mock_settings: MagicMock) -> None:
        """Test that bootstrap_vacuum_service returns VacuumService."""
        mock_settings.return_value.bronze_path = str(BRONZE_PATH)
        mock_settings.return_value.silver_path = str(SILVER_PATH)
        mock_settings.return_value.gold_path = str(GOLD_PATH)

        result = bootstrap_vacuum_service()

        from bioetl.application.services.vacuum_service import VacuumService

        assert isinstance(result, VacuumService)


@pytest.mark.unit
class TestCreateTableCollector:
    """Test _create_table_collector function."""

    def test_returns_callable(self) -> None:
        """Test that _create_table_collector returns a callable."""
        collector = _create_table_collector(registry=_registry_with_pipelines())

        assert callable(collector)

    @patch("bioetl.composition.bootstrap.cli.storage.load_pipeline_config")
    def test_collects_silver_tables(
        self,
        mock_load_config: MagicMock,
    ) -> None:
        """Test collection of silver tables."""
        # Setup mocks before creating collector
        registry = _registry_with_pipelines("pipeline1")
        mock_config = MagicMock()
        mock_config.silver_table = "silver.table1"
        mock_config.gold_table = "gold.table1"
        mock_load_config.return_value = mock_config

        collector = _create_table_collector(registry=registry)

        tables = collector("silver")

        assert len(tables) == 1
        assert tables[0] == ("silver.table1", "silver")

    @patch("bioetl.composition.bootstrap.cli.storage.load_pipeline_config")
    def test_collects_gold_tables(
        self,
        mock_load_config: MagicMock,
    ) -> None:
        """Test collection of gold tables."""
        registry = _registry_with_pipelines("pipeline1")
        mock_config = MagicMock()
        mock_config.silver_table = "silver.table1"
        mock_config.gold_table = "gold.table1"
        mock_load_config.return_value = mock_config

        collector = _create_table_collector(registry=registry)

        tables = collector("gold")

        assert len(tables) == 1
        assert tables[0] == ("gold.table1", "gold")

    @patch("bioetl.composition.bootstrap.cli.storage.load_pipeline_config")
    def test_collects_all_tables(
        self,
        mock_load_config: MagicMock,
    ) -> None:
        """Test collection of all tables."""
        registry = _registry_with_pipelines("pipeline1")
        mock_config = MagicMock()
        mock_config.silver_table = "silver.table1"
        mock_config.gold_table = "gold.table1"
        mock_load_config.return_value = mock_config

        collector = _create_table_collector(registry=registry)

        tables = collector("all")

        assert len(tables) == 2
        # Should contain both silver and gold
        layers = {t[1] for t in tables}
        assert layers == {"silver", "gold"}

    @patch("bioetl.composition.bootstrap.cli.storage.load_pipeline_config")
    def test_raises_on_missing_config(
        self,
        mock_load_config: MagicMock,
    ) -> None:
        """Test that missing pipeline config raises ValueError."""
        registry = _registry_with_pipelines("pipeline1")
        mock_load_config.side_effect = ValueError("Config not found")

        collector = _create_table_collector(registry=registry)

        # Should raise ValueError instead of silently failing
        with pytest.raises(ValueError, match="Config not found"):
            collector("all")

    @patch("bioetl.composition.bootstrap.cli.storage.load_pipeline_config")
    def test_deduplicates_tables(
        self,
        mock_load_config: MagicMock,
    ) -> None:
        """Test that duplicate tables are deduplicated."""
        # Two pipelines with same tables
        registry = _registry_with_pipelines(
            "pipeline1",
            "pipeline2",
        )
        mock_config = MagicMock()
        mock_config.silver_table = "shared.silver"
        mock_config.gold_table = "shared.gold"
        mock_load_config.return_value = mock_config

        collector = _create_table_collector(registry=registry)

        tables = collector("all")

        # Should have only 2 unique tables, not 4
        assert len(tables) == 2

    @patch("bioetl.composition.bootstrap.cli.storage.load_pipeline_config")
    def test_handles_none_tables(
        self,
        mock_load_config: MagicMock,
    ) -> None:
        """Test handling of pipelines with None tables."""
        registry = _registry_with_pipelines("pipeline1")
        mock_config = MagicMock()
        mock_config.provider = "chembl"
        mock_config.entity_type = "activity"
        mock_config.silver_table = None
        mock_config.gold_table = None
        mock_load_config.return_value = mock_config

        collector = _create_table_collector(registry=registry)

        tables = collector("all")

        # Should use fallback provider.entity when table names are omitted
        assert tables == [("chembl.activity", "silver"), ("chembl.activity", "gold")]

    @patch("bioetl.composition.bootstrap.cli.storage.load_pipeline_config")
    def test_returns_sorted_tables(
        self,
        mock_load_config: MagicMock,
    ) -> None:
        """Test that tables are returned sorted alphabetically."""
        registry = _registry_with_pipelines(
            "pipeline_z",
            "pipeline_a",
        )

        def config_for_pipeline(name: str) -> MagicMock:
            config = MagicMock()
            config.provider = "chembl"
            config.entity_type = "activity"
            if name == "pipeline_z":
                config.silver_table = "z_silver"
                config.gold_table = "z_gold"
            else:
                config.silver_table = "a_silver"
                config.gold_table = "a_gold"
            return config

        mock_load_config.side_effect = config_for_pipeline

        collector = _create_table_collector(registry=registry)

        tables = collector("silver")

        # Should be sorted: a_silver before z_silver
        table_names = [t[0] for t in tables]
        assert table_names == sorted(table_names)

    @patch("bioetl.composition.bootstrap.cli.storage.register_all_pipelines")
    @patch("bioetl.composition.bootstrap.cli.storage.create_registry")
    def test_default_collector_creates_and_registers_explicit_registry(
        self,
        mock_create_registry: MagicMock,
        mock_register_all_pipelines: MagicMock,
    ) -> None:
        """Default collector path must construct a fresh registered registry."""
        registry = _registry_with_pipelines()
        mock_create_registry.return_value = registry

        collector = _create_table_collector()

        assert callable(collector)
        mock_create_registry.assert_called_once_with()
        mock_register_all_pipelines.assert_called_once_with(registry=registry)

    @patch("bioetl.composition.bootstrap.cli.storage.load_pipeline_config")
    @patch("bioetl.composition.bootstrap.cli.storage.create_registry")
    @patch("bioetl.composition.bootstrap.cli.storage.register_all_pipelines")
    def test_explicit_registry_bypasses_default_registry_lookup(
        self,
        mock_register_all_pipelines: MagicMock,
        mock_create_registry: MagicMock,
        mock_load_config: MagicMock,
    ) -> None:
        """Explicit registry injection should avoid fallback registry creation."""
        registry = _registry_with_pipelines("pipeline1")
        mock_config = MagicMock()
        mock_config.silver_table = "silver.table1"
        mock_config.gold_table = "gold.table1"
        mock_load_config.return_value = mock_config

        collector = _create_table_collector(registry=registry)

        tables = collector("all")

        assert tables == [("silver.table1", "silver"), ("gold.table1", "gold")]
        mock_create_registry.assert_not_called()
        mock_register_all_pipelines.assert_not_called()
