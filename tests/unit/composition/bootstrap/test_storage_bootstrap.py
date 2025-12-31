"""Tests for storage bootstrap functions.

Tests the bootstrap functions for storage components used by CLI operations.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from bioetl.composition._bootstrap.storage import (
    _create_table_collector,
    bootstrap_bronze_cleanup_service,
    bootstrap_cleanup,
    bootstrap_lifecycle_service,
    bootstrap_storage,
    bootstrap_vacuum_service,
)
from bioetl.composition.factories.storage import StorageAdapter
from bioetl.infrastructure.observability.noop_logger import NoOpLogger


@pytest.mark.unit
class TestBootstrapStorage:
    """Test bootstrap_storage function."""

    @patch("bioetl.composition._bootstrap.storage.get_settings")
    def test_returns_storage_adapter(self, mock_settings: MagicMock) -> None:
        """Test that bootstrap_storage returns a StorageAdapter."""
        mock_settings.return_value.bronze_path = "/tmp/bronze"
        mock_settings.return_value.silver_path = "/tmp/silver"
        mock_settings.return_value.gold_path = "/tmp/gold"

        result = bootstrap_storage()

        assert isinstance(result, StorageAdapter)


@pytest.mark.unit
class TestBootstrapCleanup:
    """Test bootstrap_cleanup function."""

    @patch("bioetl.composition._bootstrap.storage.get_settings")
    def test_returns_cleanup_service(self, mock_settings: MagicMock) -> None:
        """Test that bootstrap_cleanup returns a CleanupService."""
        mock_settings.return_value.bronze_path = "/tmp/bronze"
        mock_settings.return_value.silver_path = "/tmp/silver"
        mock_settings.return_value.gold_path = "/tmp/gold"

        result = bootstrap_cleanup()

        from bioetl.application.core.cleanup_service import CleanupService

        assert isinstance(result, CleanupService)


@pytest.mark.unit
class TestBootstrapLifecycleService:
    """Test bootstrap_lifecycle_service function."""

    @patch("bioetl.composition._bootstrap.storage.get_settings")
    def test_returns_medallion_lifecycle_service(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test that bootstrap_lifecycle_service returns MedallionLifecycleService."""
        mock_settings.return_value.bronze_path = "/tmp/bronze"
        mock_settings.return_value.silver_path = "/tmp/silver"
        mock_settings.return_value.gold_path = "/tmp/gold"

        result = bootstrap_lifecycle_service()

        from bioetl.application.services.medallion_lifecycle import (
            MedallionLifecycleService,
        )

        assert isinstance(result, MedallionLifecycleService)


@pytest.mark.unit
class TestBootstrapBronzeCleanupService:
    """Test bootstrap_bronze_cleanup_service function."""

    @patch("bioetl.composition._bootstrap.storage.get_settings")
    def test_returns_bronze_cleanup_service(
        self,
        mock_settings: MagicMock,
    ) -> None:
        """Test that bootstrap_bronze_cleanup_service returns BronzeCleanupService."""
        mock_settings.return_value.bronze_path = "/tmp/bronze"
        mock_settings.return_value.silver_path = "/tmp/silver"
        mock_settings.return_value.gold_path = "/tmp/gold"

        result = bootstrap_bronze_cleanup_service()

        from bioetl.application.services import BronzeCleanupService

        assert isinstance(result, BronzeCleanupService)


@pytest.mark.unit
class TestBootstrapVacuumService:
    """Test bootstrap_vacuum_service function."""

    @patch("bioetl.composition._bootstrap.storage.get_settings")
    def test_returns_vacuum_service(self, mock_settings: MagicMock) -> None:
        """Test that bootstrap_vacuum_service returns VacuumService."""
        mock_settings.return_value.bronze_path = "/tmp/bronze"
        mock_settings.return_value.silver_path = "/tmp/silver"
        mock_settings.return_value.gold_path = "/tmp/gold"

        result = bootstrap_vacuum_service()

        from bioetl.application.services import VacuumService

        assert isinstance(result, VacuumService)


@pytest.mark.unit
class TestCreateTableCollector:
    """Test _create_table_collector function."""

    def test_returns_callable(self) -> None:
        """Test that _create_table_collector returns a callable."""
        logger = NoOpLogger()
        collector = _create_table_collector(logger)

        assert callable(collector)

    @patch("bioetl.composition.entrypoints.load_pipeline_config")
    @patch("bioetl.composition.registry.get_default_registry")
    def test_collects_silver_tables(
        self,
        mock_registry: MagicMock,
        mock_load_config: MagicMock,
    ) -> None:
        """Test collection of silver tables."""
        # Setup mocks before creating collector
        mock_registry.return_value.list_pipelines.return_value = ["pipeline1"]
        mock_config = MagicMock()
        mock_config.silver_table = "silver.table1"
        mock_config.gold_table = "gold.table1"
        mock_load_config.return_value = mock_config

        logger = NoOpLogger()
        collector = _create_table_collector(logger)

        tables = collector("silver")

        assert len(tables) == 1
        assert tables[0] == ("silver.table1", "silver")

    @patch("bioetl.composition.entrypoints.load_pipeline_config")
    @patch("bioetl.composition.registry.get_default_registry")
    def test_collects_gold_tables(
        self,
        mock_registry: MagicMock,
        mock_load_config: MagicMock,
    ) -> None:
        """Test collection of gold tables."""
        mock_registry.return_value.list_pipelines.return_value = ["pipeline1"]
        mock_config = MagicMock()
        mock_config.silver_table = "silver.table1"
        mock_config.gold_table = "gold.table1"
        mock_load_config.return_value = mock_config

        logger = NoOpLogger()
        collector = _create_table_collector(logger)

        tables = collector("gold")

        assert len(tables) == 1
        assert tables[0] == ("gold.table1", "gold")

    @patch("bioetl.composition.entrypoints.load_pipeline_config")
    @patch("bioetl.composition.registry.get_default_registry")
    def test_collects_all_tables(
        self,
        mock_registry: MagicMock,
        mock_load_config: MagicMock,
    ) -> None:
        """Test collection of all tables."""
        mock_registry.return_value.list_pipelines.return_value = ["pipeline1"]
        mock_config = MagicMock()
        mock_config.silver_table = "silver.table1"
        mock_config.gold_table = "gold.table1"
        mock_load_config.return_value = mock_config

        logger = NoOpLogger()
        collector = _create_table_collector(logger)

        tables = collector("all")

        assert len(tables) == 2
        # Should contain both silver and gold
        layers = {t[1] for t in tables}
        assert layers == {"silver", "gold"}

    @patch("bioetl.composition.entrypoints.load_pipeline_config")
    @patch("bioetl.composition.registry.get_default_registry")
    def test_handles_missing_config(
        self,
        mock_registry: MagicMock,
        mock_load_config: MagicMock,
    ) -> None:
        """Test handling of missing pipeline config."""
        mock_registry.return_value.list_pipelines.return_value = ["pipeline1"]
        mock_load_config.side_effect = FileNotFoundError("Config not found")

        logger = MagicMock()
        collector = _create_table_collector(logger)

        tables = collector("all")

        # Should return empty list and log warning
        assert tables == []
        logger.warning.assert_called_once()

    @patch("bioetl.composition.entrypoints.load_pipeline_config")
    @patch("bioetl.composition.registry.get_default_registry")
    def test_deduplicates_tables(
        self,
        mock_registry: MagicMock,
        mock_load_config: MagicMock,
    ) -> None:
        """Test that duplicate tables are deduplicated."""
        # Two pipelines with same tables
        mock_registry.return_value.list_pipelines.return_value = [
            "pipeline1",
            "pipeline2",
        ]
        mock_config = MagicMock()
        mock_config.silver_table = "shared.silver"
        mock_config.gold_table = "shared.gold"
        mock_load_config.return_value = mock_config

        logger = NoOpLogger()
        collector = _create_table_collector(logger)

        tables = collector("all")

        # Should have only 2 unique tables, not 4
        assert len(tables) == 2

    @patch("bioetl.composition.entrypoints.load_pipeline_config")
    @patch("bioetl.composition.registry.get_default_registry")
    def test_handles_none_tables(
        self,
        mock_registry: MagicMock,
        mock_load_config: MagicMock,
    ) -> None:
        """Test handling of pipelines with None tables."""
        mock_registry.return_value.list_pipelines.return_value = ["pipeline1"]
        mock_config = MagicMock()
        mock_config.silver_table = None
        mock_config.gold_table = None
        mock_load_config.return_value = mock_config

        logger = NoOpLogger()
        collector = _create_table_collector(logger)

        tables = collector("all")

        # Should return empty list when tables are None
        assert tables == []

    @patch("bioetl.composition.entrypoints.load_pipeline_config")
    @patch("bioetl.composition.registry.get_default_registry")
    def test_returns_sorted_tables(
        self,
        mock_registry: MagicMock,
        mock_load_config: MagicMock,
    ) -> None:
        """Test that tables are returned sorted alphabetically."""
        mock_registry.return_value.list_pipelines.return_value = [
            "pipeline_z",
            "pipeline_a",
        ]

        def config_for_pipeline(name: str) -> MagicMock:
            config = MagicMock()
            if name == "pipeline_z":
                config.silver_table = "z_silver"
                config.gold_table = "z_gold"
            else:
                config.silver_table = "a_silver"
                config.gold_table = "a_gold"
            return config

        mock_load_config.side_effect = config_for_pipeline

        logger = NoOpLogger()
        collector = _create_table_collector(logger)

        tables = collector("silver")

        # Should be sorted: a_silver before z_silver
        table_names = [t[0] for t in tables]
        assert table_names == sorted(table_names)
