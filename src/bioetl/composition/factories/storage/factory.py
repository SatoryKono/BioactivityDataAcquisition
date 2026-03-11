"""StorageFactory - thin facade for creating StorageAdapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

from ._helpers import (
    create_layer_exporters,
    create_storage_adapter,
    get_layer_configs,
    log_configured_export_status,
    resolve_flat_structure_flags,
    resolve_storage_paths,
)
from .adapter import StorageAdapter

if TYPE_CHECKING:
    from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
    from bioetl.domain.ports import (
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
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
    def create(
        settings: Settings,
        config: PipelineYamlConfig,
        logger: LoggerPort,
        metrics: MetricsPort,
        tracing: TracingPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        silver_validator: SilverValidatorPort | None = None,
    ) -> StorageContext:
        """Create local storage context with configured layer writers.

        Args:
            settings: Application settings providing base paths, test_mode, and
                resilience configuration.
            config: Pipeline YAML configuration with sink layer definitions.
            logger: LoggerPort for structured logging and export status events.
            metrics: MetricsPort for storage metrics collection.
            tracing: Optional TracingPort; defaults to NoOpTracing if None.
            metadata_coordinator: Optional coordinator for metadata side-effects;
                defaults to None.
            silver_validator: Optional PyArrow schema validator for Silver records;
                defaults to None.

        Returns:
            StorageContext with assembled adapter and resolved layer paths.
        """
        bronze_config, silver_config, gold_config = get_layer_configs(config)
        use_yaml_paths, bronze_path, silver_path, gold_path = resolve_storage_paths(
            settings=settings,
            bronze_config=bronze_config,
            silver_config=silver_config,
            gold_config=gold_config,
        )
        logger.info(
            "Using local storage",
            bronze_path=str(bronze_path),
            silver_path=str(silver_path),
            gold_path=str(gold_path),
        )
        silver_csv_exporter, gold_csv_exporter = create_layer_exporters(
            settings=settings,
            logger=logger,
            silver_config=silver_config,
            gold_config=gold_config,
            silver_path=silver_path,
            gold_path=gold_path,
        )
        log_configured_export_status(
            logger=logger,
            bronze_config=bronze_config,
            silver_config=silver_config,
            gold_config=gold_config,
            silver_csv_exporter=silver_csv_exporter,
            gold_csv_exporter=gold_csv_exporter,
        )
        (
            bronze_flat_structure,
            silver_flat_structure,
            gold_flat_structure,
        ) = resolve_flat_structure_flags(
            bronze_config=bronze_config,
            silver_config=silver_config,
            gold_config=gold_config,
            use_yaml_paths=use_yaml_paths,
        )
        adapter = create_storage_adapter(
            bronze_writer_cls=BronzeWriter,
            silver_writer_cls=SilverWriter,
            gold_writer_cls=GoldWriter,
            settings=settings,
            config=config,
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
            silver_validator=silver_validator,
            bronze_flat_structure=bronze_flat_structure,
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
