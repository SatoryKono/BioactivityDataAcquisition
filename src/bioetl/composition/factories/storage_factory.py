"""StorageFactory - thin facade for creating StorageAdapters."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

from ._bronze_factory import create_bronze_writer
from ._gold_factory import create_gold_writer
from ._silver_factory import create_silver_writer
from .storage_adapter import StorageAdapter

if TYPE_CHECKING:
    from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
    from bioetl.domain.ports import (
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import (
        PipelineYamlConfig,
        SinkLayerConfig,
    )


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
    def _create_csv_exporter_from_config(
        csv_cfg: object | None,
        logger: LoggerPort,
        override_path: Path | None = None,
    ) -> CsvExporter | None:
        """Create CsvExporter from configuration when export is enabled."""
        if not (csv_cfg and getattr(csv_cfg, "enabled", False)):
            return None
        path = override_path or getattr(csv_cfg, "path", None)
        if path is None:
            return None
        return CsvExporter(
            base_path=str(path),
            logger=logger,
            delimiter=str(getattr(csv_cfg, "delimiter", ",")),
            header=bool(getattr(csv_cfg, "header", True)),
            encoding=str(getattr(csv_cfg, "encoding", "utf-8")),
        )

    @staticmethod
    def _resolve_layer_path(
        layer_config: SinkLayerConfig | None,
        default_path: Path,
        use_yaml_paths: bool,
    ) -> Path:
        """Resolve storage path from sink config or fall back to default."""
        if use_yaml_paths and layer_config and layer_config.path:
            return Path(layer_config.path)
        return default_path

    @staticmethod
    def _log_export_status(
        logger: LoggerPort,
        save_json: bool,
        silver_csv_exporter: CsvExporter | None,
        gold_csv_exporter: CsvExporter | None,
        bronze_save_metadata: bool,
        silver_save_metadata: bool,
        gold_save_metadata: bool,
    ) -> None:
        """Log active export settings for observability."""
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

    @staticmethod
    def _create_storage_adapter(
        *,
        bronze_path: Path,
        silver_path: Path,
        gold_path: Path,
        bronze_config: SinkLayerConfig | None,
        silver_config: SinkLayerConfig | None,
        gold_config: SinkLayerConfig | None,
        silver_csv_exporter: CsvExporter | None,
        gold_csv_exporter: CsvExporter | None,
        logger: LoggerPort,
        metrics: MetricsPort,
        tracing: TracingPort | None,
        metadata_coordinator: MetadataCoordinator | None,
        transform_version: str | None,
        transform_steps: tuple[str, ...],
        bronze_flat_structure: bool,
        silver_flat_structure: bool,
        gold_flat_structure: bool,
        silver_validator: SilverValidatorPort | None,
    ) -> StorageAdapter:
        """Create StorageAdapter with Bronze/Silver/Gold writers."""
        bronze_writer = create_bronze_writer(
            writer_cls=BronzeWriter,
            base_path=bronze_path,
            config=bronze_config,
            logger=logger,
            metrics=metrics,
            tracing=tracing,
            metadata_coordinator=metadata_coordinator,
            flat_structure=bronze_flat_structure,
        )
        silver_writer = create_silver_writer(
            writer_cls=SilverWriter,
            base_path=silver_path,
            config=silver_config,
            logger=logger,
            tracing=tracing,
            csv_exporter=silver_csv_exporter,
            metadata_coordinator=metadata_coordinator,
            transform_version=transform_version,
            transform_steps=transform_steps,
            flat_structure=silver_flat_structure,
            silver_validator=silver_validator,
        )
        gold_writer = create_gold_writer(
            writer_cls=GoldWriter,
            base_path=gold_path,
            config=gold_config,
            logger=logger,
            tracing=tracing,
            csv_exporter=gold_csv_exporter,
            metadata_coordinator=metadata_coordinator,
            transform_version=transform_version,
            transform_steps=transform_steps,
            flat_structure=gold_flat_structure,
        )
        return StorageAdapter(
            bronze_writer=bronze_writer,
            silver_writer=silver_writer,
            gold_writer=gold_writer,
        )

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
        """Create local storage context with configured layer writers."""
        bronze_config = config.sink.get("bronze")
        silver_config = config.sink.get("silver")
        gold_config = config.sink.get("gold")

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

        save_json = bronze_config.save_json if bronze_config else False
        bronze_save_metadata = bronze_config.save_metadata if bronze_config else False
        silver_save_metadata = silver_config.save_metadata if silver_config else False
        gold_save_metadata = gold_config.save_metadata if gold_config else False
        StorageFactory._log_export_status(
            logger=logger,
            save_json=save_json,
            silver_csv_exporter=silver_csv_exporter,
            gold_csv_exporter=gold_csv_exporter,
            bronze_save_metadata=bronze_save_metadata,
            silver_save_metadata=silver_save_metadata,
            gold_save_metadata=gold_save_metadata,
        )

        bronze_flat_structure = (
            bronze_config.flat_structure if bronze_config else False
        ) and use_yaml_paths
        silver_flat_structure = (
            silver_config.flat_structure if silver_config else False
        ) and use_yaml_paths
        gold_flat_structure = (
            gold_config.flat_structure if gold_config else False
        ) and use_yaml_paths

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
            transform_version=config.transform.version,
            transform_steps=tuple(config.transform.steps),
            bronze_flat_structure=bronze_flat_structure,
            silver_flat_structure=silver_flat_structure,
            gold_flat_structure=gold_flat_structure,
            silver_validator=silver_validator,
        )
        return StorageContext(
            adapter=adapter,
            bronze_path=bronze_path,
            silver_path=silver_path,
            gold_path=gold_path,
            checkpoints_path=settings.checkpoint_path,
        )
