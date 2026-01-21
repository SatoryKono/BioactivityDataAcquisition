"""StorageFactory - Factory for creating StorageAdapters.

Creates configured StorageAdapters for local deployment with proper
Bronze, Silver, and Gold writers.

This module was extracted from storage.py as part of the storage factory split
to improve maintainability and reduce file size.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.domain.ports import NoOpMetadataWriter
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.observability.noop_tracing import NoOpTracing
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

from .storage_adapter import StorageAdapter

if TYPE_CHECKING:
    from typing import Any

    from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
    from bioetl.domain.ports import LoggerPort, MetricsPort, TracingPort
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


__all__ = ["StorageContext", "StorageFactory"]


@dataclass(frozen=True)
class StorageContext:
    """Context object returned by StorageFactory containing adapter and paths."""

    adapter: StorageAdapter
    bronze_path: Path
    silver_path: Path
    gold_path: Path
    checkpoints_path: Path


class StorageFactory:
    """Factory for creating configured StorageAdapters for local deployment."""

    @staticmethod
    def _create_metadata_writer(
        enabled: bool, logger: LoggerPort
    ) -> MetadataWriter | NoOpMetadataWriter:
        """Create a MetadataWriter or NoOp based on configuration."""
        if enabled:
            return MetadataWriter(logger=logger)
        return NoOpMetadataWriter()

    @staticmethod
    def _create_csv_exporter_from_config(
        csv_cfg: Any,
        logger: LoggerPort,
        override_path: Path | None = None,
    ) -> CsvExporter | None:
        """Create a CsvExporter from configuration if enabled.

        Args:
            csv_cfg: CSV export configuration from YAML.
            logger: Logger for observability.
            override_path: If provided, use this path instead of csv_cfg.path.
                          Used in test mode to respect test isolation.
        """
        if csv_cfg and csv_cfg.enabled:
            # Convert to str for CsvExporter (expects str, not Path)
            path = override_path or csv_cfg.path
            return CsvExporter(
                base_path=str(path),
                logger=logger,
                delimiter=csv_cfg.delimiter,
                header=csv_cfg.header,
                encoding=csv_cfg.encoding,
            )
        return None

    @staticmethod
    def _resolve_layer_path(
        layer_config: Any, default_path: Path, use_yaml_paths: bool
    ) -> Path:
        """Resolve storage path from config or fall back to default."""
        if use_yaml_paths and layer_config and layer_config.path:
            return Path(layer_config.path)
        return default_path

    @staticmethod
    def _create_storage_adapter(
        bronze_path: Path,
        silver_path: Path,
        gold_path: Path,
        bronze_config: Any,
        silver_config: Any,
        gold_config: Any,
        silver_csv_exporter: CsvExporter | None,
        gold_csv_exporter: CsvExporter | None,
        logger: LoggerPort,
        metrics: MetricsPort,
        tracing: TracingPort | None,
        metadata_coordinator: MetadataCoordinator | None = None,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
        silver_flat_structure: bool = False,
        gold_flat_structure: bool = False,
    ) -> StorageAdapter:
        """Create StorageAdapter with all writers configured.

        Note:
            Lock validation is performed at Application layer (BatchWriter)
            per RULES.md §4.6 Safety Guard. Infrastructure writers are pure I/O.
        """
        save_json = bronze_config.save_json if bronze_config else False
        bronze_save_metadata = bronze_config.save_metadata if bronze_config else False
        # JSON files are now written alongside zst files (same directory)
        # No separate json_path needed

        # Ensure tracing is always explicitly provided (DI pattern)
        effective_tracing: TracingPort = tracing or NoOpTracing()

        # Create metadata writers using Null Object pattern
        silver_save_metadata = silver_config.save_metadata if silver_config else False
        gold_save_metadata = gold_config.save_metadata if gold_config else False

        bronze_metadata_writer = StorageFactory._create_metadata_writer(
            bronze_save_metadata, logger
        )
        silver_metadata_writer = StorageFactory._create_metadata_writer(
            silver_save_metadata, logger
        )
        gold_metadata_writer = StorageFactory._create_metadata_writer(
            gold_save_metadata, logger
        )

        return StorageAdapter(
            bronze_writer=BronzeWriter(
                base_path=bronze_path,
                logger=logger,
                metrics=metrics,
                tracing=effective_tracing,
                save_json=save_json,
                json_path=None,  # JSON is now written alongside zst files
                metadata_writer=bronze_metadata_writer,
                save_metadata=bronze_save_metadata,
                metadata_coordinator=metadata_coordinator,
            ),
            silver_writer=SilverWriter(
                base_path=silver_path,
                logger=logger,
                tracing=effective_tracing,
                csv_exporter=silver_csv_exporter,
                metadata_writer=silver_metadata_writer,
                metadata_coordinator=metadata_coordinator,
                transform_version=transform_version,
                transform_steps=transform_steps,
                flat_structure=silver_flat_structure,
            ),
            gold_writer=GoldWriter(
                base_path=gold_path,
                logger=logger,
                tracing=effective_tracing,
                csv_exporter=gold_csv_exporter,
                metadata_writer=gold_metadata_writer,
                metadata_coordinator=metadata_coordinator,
                transform_version=transform_version,
                transform_steps=transform_steps,
                flat_structure=gold_flat_structure,
            ),
        )

    @staticmethod
    def create(
        settings: Settings,
        config: PipelineYamlConfig,
        logger: LoggerPort,
        metrics: MetricsPort,
        tracing: TracingPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
    ) -> StorageContext:
        """Create a StorageAdapter for local deployment.

        Args:
            settings: Application settings with data_dir
            config: Pipeline YAML configuration
            logger: Structured logger
            metrics: Metrics port for Bronze observability (MUST be injected).
            tracing: Optional TracingPort for distributed tracing.
            metadata_coordinator: Optional MetadataCoordinator for centralized
                                metadata creation. If provided, ensures consistent
                                run_id and timestamps across Bronze, Silver, Gold.

        Returns:
            StorageContext with adapter and paths
        """
        bronze_config = config.sink.get("bronze")
        silver_config = config.sink.get("silver")
        gold_config = config.sink.get("gold")

        # In test mode, always use settings to respect test isolation
        use_yaml_paths = not settings.test_mode

        bronze_path = StorageFactory._resolve_layer_path(
            bronze_config, settings.bronze_path, use_yaml_paths
        )
        silver_path = StorageFactory._resolve_layer_path(
            silver_config, settings.silver_path, use_yaml_paths
        )
        gold_path = StorageFactory._resolve_layer_path(
            gold_config, settings.gold_path, use_yaml_paths
        )

        logger.info(
            "Using local storage",
            bronze_path=str(bronze_path),
            silver_path=str(silver_path),
            gold_path=str(gold_path),
        )

        # In test mode, override CSV export paths to use resolved layer paths
        # This ensures test isolation by writing to temp directories
        silver_csv_exporter = StorageFactory._create_csv_exporter_from_config(
            silver_config.csv_export if silver_config else None,
            logger,
            override_path=silver_path if settings.test_mode else None,
        )
        gold_csv_exporter = StorageFactory._create_csv_exporter_from_config(
            gold_config.csv_export if gold_config else None,
            logger,
            override_path=gold_path if settings.test_mode else None,
        )

        # JSON files are now written alongside zst files (same directory)
        save_json = bronze_config.save_json if bronze_config else False

        bronze_save_metadata = bronze_config.save_metadata if bronze_config else False
        silver_save_metadata = silver_config.save_metadata if silver_config else False
        gold_save_metadata = gold_config.save_metadata if gold_config else False
        StorageFactory._log_export_status(
            logger,
            save_json,
            silver_csv_exporter,
            gold_csv_exporter,
            bronze_save_metadata,
            silver_save_metadata,
            gold_save_metadata,
        )

        # Extract transform info for lineage tracking
        transform_version = config.transform.version
        transform_steps = tuple(config.transform.steps)

        # Extract flat_structure settings
        silver_flat_structure = silver_config.flat_structure if silver_config else False
        gold_flat_structure = gold_config.flat_structure if gold_config else False

        adapter = StorageFactory._create_storage_adapter(
            bronze_path=bronze_path,
            silver_path=silver_path,
            gold_path=gold_path,
            bronze_config=bronze_config,
            silver_config=silver_config,
            gold_config=gold_config,
            silver_csv_exporter=silver_csv_exporter,
            gold_csv_exporter=gold_csv_exporter,
            logger=logger,
            metrics=metrics,
            tracing=tracing,
            metadata_coordinator=metadata_coordinator,
            transform_version=transform_version,
            transform_steps=transform_steps,
            silver_flat_structure=silver_flat_structure,
            gold_flat_structure=gold_flat_structure,
        )

        return StorageContext(
            adapter=adapter,
            bronze_path=bronze_path,
            silver_path=silver_path,
            gold_path=gold_path,
            checkpoints_path=settings.checkpoint_path,
        )

    @staticmethod
    def _log_export_status(
        logger: LoggerPort,
        save_json: bool,
        silver_csv_exporter: CsvExporter | None,
        gold_csv_exporter: CsvExporter | None,
        bronze_save_metadata: bool = False,
        silver_save_metadata: bool = False,
        gold_save_metadata: bool = False,
    ) -> None:
        """Log export configuration status."""
        if save_json:
            logger.info("JSON export enabled for Bronze layer (alongside zst files)")
        if bronze_save_metadata:
            logger.info("metadata_export_enabled", layer="bronze")
        if silver_save_metadata:
            logger.info("metadata_export_enabled", layer="silver")
        if gold_save_metadata:
            logger.info("metadata_export_enabled", layer="gold")
        if silver_csv_exporter:
            logger.info(
                "csv_export_enabled",
                layer="silver",
                base_path=str(silver_csv_exporter.base_path),
            )
        if gold_csv_exporter:
            logger.info(
                "csv_export_enabled",
                layer="gold",
                base_path=str(gold_csv_exporter.base_path),
            )
