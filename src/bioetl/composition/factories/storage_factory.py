"""Unified storage factory for Bronze/Silver/Gold layers.

Contains StorageContext and StorageFactory for creating configured
local storage infrastructure. StorageAdapter is defined in storage_adapter.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.composition.factories.storage_adapter import StorageAdapter
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter

if TYPE_CHECKING:
    from typing import Any

    import structlog

    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

# Re-export StorageAdapter for backward compatibility
__all__ = ["StorageAdapter", "StorageContext", "StorageFactory"]


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
    def _create_csv_exporter_from_config(csv_cfg: Any) -> CsvExporter | None:
        """Create a CsvExporter from configuration if enabled."""
        if csv_cfg and csv_cfg.enabled:
            return CsvExporter(
                base_path=csv_cfg.path,
                delimiter=csv_cfg.delimiter,
                header=csv_cfg.header,
                encoding=csv_cfg.encoding,
            )
        return None

    @staticmethod
    def create(
        settings: Settings,
        config: PipelineYamlConfig,
        logger: structlog.BoundLogger,
    ) -> StorageContext:
        """Create a StorageAdapter for local deployment.

        Args:
            settings: Application settings with data_dir
            config: Pipeline YAML configuration
            logger: Structured logger

        Returns:
            StorageContext with adapter and paths
        """
        bronze_path = settings.bronze_path
        silver_path = settings.silver_path
        gold_path = settings.gold_path
        checkpoints_path = settings.checkpoint_path

        bronze_config = config.sink.get("bronze")
        silver_config = config.sink.get("silver")
        gold_config = config.sink.get("gold")

        json_path = None
        silver_csv_exporter: CsvExporter | None = None
        gold_csv_exporter: CsvExporter | None = None

        logger.info(
            "Using local storage",
            bronze_path=str(bronze_path),
            silver_path=str(silver_path),
            gold_path=str(gold_path),
        )

        if bronze_config and bronze_config.save_json:
            json_path = str(settings.data_dir / "json")

        if silver_config:
            silver_csv_exporter = StorageFactory._create_csv_exporter_from_config(
                silver_config.csv_export
            )
        if gold_config:
            gold_csv_exporter = StorageFactory._create_csv_exporter_from_config(
                gold_config.csv_export
            )

        StorageFactory._log_export_status(
            logger, json_path, silver_csv_exporter, gold_csv_exporter
        )
        save_json = bronze_config.save_json if bronze_config else False

        adapter = StorageAdapter(
            bronze_writer=BronzeWriter(
                base_path=bronze_path,
                logger=logger,
                save_json=save_json,
                json_path=json_path,
            ),
            silver_writer=DeltaWriter(
                base_path=silver_path,
                logger=logger,
                csv_exporter=silver_csv_exporter,
            ),
            gold_writer=GoldWriter(
                base_path=gold_path,
                logger=logger,
                csv_exporter=gold_csv_exporter,
            ),
        )

        return StorageContext(
            adapter=adapter,
            bronze_path=bronze_path,
            silver_path=silver_path,
            gold_path=gold_path,
            checkpoints_path=checkpoints_path,
        )

    @staticmethod
    def _log_export_status(
        logger: structlog.BoundLogger,
        json_path: str | None,
        silver_csv_exporter: CsvExporter | None,
        gold_csv_exporter: CsvExporter | None,
    ) -> None:
        """Log export configuration status."""
        if json_path:
            logger.info("JSON export enabled for Bronze layer")
        if silver_csv_exporter:
            logger.info(
                f"CSV export enabled for Silver layer: {silver_csv_exporter.base_path}"
            )
        if gold_csv_exporter:
            logger.info(
                f"CSV export enabled for Gold layer: {gold_csv_exporter.base_path}"
            )
