"""Unified storage factory for Bronze/Silver/Gold layers.

Contains StorageAdapter, StorageContext, and StorageFactory for creating
configured storage infrastructure.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter

if TYPE_CHECKING:
    from collections.abc import Iterator
    from datetime import datetime

    import structlog

    from bioetl.domain.types import ArrowSchema, BatchID, RunID, RunType
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


class StorageAdapter:
    """Unified storage adapter for Bronze/Silver/Gold.

    Implements StoragePort protocol from domain/ports.py.
    """

    # Protocol compliance marker
    REQUIRES_SILVER_SCHEMA: bool = True

    def __init__(
        self,
        bronze_writer: BronzeWriter,
        silver_writer: DeltaWriter,
        gold_writer: GoldWriter,
    ):
        self.bronze = bronze_writer
        self.silver = silver_writer
        self.gold = gold_writer

    async def write_bronze(
        self,
        records: Iterator[bytes],
        provider: str,
        entity: str,
        date: datetime,
        batch_id: BatchID,
        run_id: RunID,
        run_type: RunType,
    ) -> None:
        """Write raw records to Bronze layer."""
        await self.bronze.write_bronze(
            records=records,
            provider=provider,
            entity=entity,
            date=date,
            batch_id=batch_id,
            run_id=run_id,
            run_type=run_type,
        )

    async def write_silver(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str],
        schema: ArrowSchema,
        mode: Literal["merge", "append", "delete"] = "merge",
        partition_cols: list[str] | None = None,
    ) -> None:
        """Write transformed records to Silver layer."""
        await self.silver.write_silver(
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            schema=schema,
            mode=mode,
            partition_cols=partition_cols,
        )

    async def write_gold(
        self,
        table_name: str,
        records: list[dict[str, Any]],
        primary_keys: list[str] | None = None,
        mode: Literal["overwrite", "append", "scd2"] = "overwrite",
    ) -> None:
        """Write aggregated records to Gold layer."""
        await self.gold.write_gold(
            table_name=table_name,
            records=records,
            primary_keys=primary_keys,
            mode=mode,
        )

    def clear_csv(self, table_name: str | None = None) -> int:
        """Clear CSV export files for Silver and Gold layers.

        Should be called at the start of a pipeline run to ensure
        fresh CSV exports without duplicates from previous runs.

        Args:
            table_name: If provided, only clear CSV for this table.
                       If None, clear all CSV files.

        Returns:
            Total number of files deleted.
        """
        deleted_count = 0

        # Clear Silver CSV if exporter is configured
        if self.silver.csv_exporter:
            deleted = self.silver.csv_exporter.clear(table_name)
            deleted_count += len(deleted)

        # Clear Gold CSV if exporter is configured
        if self.gold.csv_exporter:
            deleted = self.gold.csv_exporter.clear(table_name)
            deleted_count += len(deleted)

        return deleted_count

    def clear_delta(self, table_name: str | None = None) -> int:
        """Clear Delta tables for Silver and Gold layers.

        Should be called at the start of a pipeline run to ensure
        fresh data without duplicates from previous runs.

        Args:
            table_name: If provided, only clear Delta table for this table.
                       If None, clear all Delta tables.

        Returns:
            Total number of tables cleared.
        """
        cleared_count = 0

        # Clear Silver Delta table
        cleared_count += self.silver.clear(table_name)

        # Clear Gold Delta table
        cleared_count += self.gold.clear(table_name)

        return cleared_count

    async def aclose(self) -> None:
        """Close resources.

        Implements aclose() required by StoragePort protocol.
        """
        pass  # Writers don't need explicit cleanup


@dataclass(frozen=True)
class StorageContext:
    """Context object returned by StorageFactory containing adapter and paths."""

    adapter: StorageAdapter
    bronze_path: str
    silver_path: str
    gold_path: str
    checkpoints_path: str


class StorageFactory:
    """Factory for creating configured StorageAdapters."""

    @staticmethod
    def create(
        settings: Settings,
        config: PipelineYamlConfig,
        logger: structlog.BoundLogger,
    ) -> StorageContext:
        """Create a StorageAdapter based on environment and pipeline configuration.

        Handles path resolution for local vs cloud runs and configures
        CSV/JSON export options for local debugging.

        Args:
            settings: Application settings
            config: Typed pipeline configuration
            logger: Structured logger

        Returns:
            StorageContext containing adapter and resolved paths
        """
        # Import here to avoid circular imports during module loading
        from bioetl.composition.factories.clients import get_aws_credentials

        is_local_run = settings.env != "prod" and not settings.aws.endpoint_url
        aws_config = settings.aws
        s3_config = settings.s3
        storage_options = settings.storage_options if not is_local_run else None
        access_key, secret_key = get_aws_credentials(settings)

        # Extract sink configs
        bronze_config = config.sink.get("bronze")
        silver_config = config.sink.get("silver")
        gold_config = config.sink.get("gold")

        # Initialize export variables
        json_path = None
        silver_csv_exporter: CsvExporter | None = None
        gold_csv_exporter: CsvExporter | None = None

        if is_local_run:
            logger.info(
                "Local run detected. Overriding storage paths to 'data/output'."
            )
            base_output_path = "data/output"
            bronze_path = f"{base_output_path}/bronze"
            silver_base_path = f"{base_output_path}/silver"
            gold_base_path = f"{base_output_path}/gold"
            checkpoints_path = f"{base_output_path}/checkpoints"

            # Handle JSON export (Bronze)
            if bronze_config and bronze_config.save_json:
                json_path = f"{base_output_path}/json"

            # Handle CSV export (Silver)
            if silver_config and silver_config.csv_export.enabled:
                csv_cfg = silver_config.csv_export
                silver_csv_exporter = CsvExporter(
                    base_path=csv_cfg.path,
                    delimiter=csv_cfg.delimiter,
                    header=csv_cfg.header,
                    encoding=csv_cfg.encoding,
                )

            # Handle CSV export (Gold)
            if gold_config and gold_config.csv_export.enabled:
                csv_cfg = gold_config.csv_export
                gold_csv_exporter = CsvExporter(
                    base_path=csv_cfg.path,
                    delimiter=csv_cfg.delimiter,
                    header=csv_cfg.header,
                    encoding=csv_cfg.encoding,
                )
        else:
            # Cloud paths
            bronze_path = s3_config.bucket_bronze
            silver_base_path = f"s3://{s3_config.bucket_silver}"
            gold_base_path = f"s3://{s3_config.bucket_gold}"
            checkpoints_path = s3_config.bucket_checkpoints

        # Logging
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

        # Determine save_json flag
        save_json = bronze_config.save_json if bronze_config else False

        adapter = StorageAdapter(
            bronze_writer=BronzeWriter(
                bucket=bronze_path,
                endpoint_url=aws_config.endpoint_url if not is_local_run else None,
                access_key=access_key,
                secret_key=secret_key,
                save_json=save_json,
                json_path=json_path,
                logger=logger,
            ),
            silver_writer=DeltaWriter(
                base_path=silver_base_path,
                storage_options=storage_options,
                csv_exporter=silver_csv_exporter,
            ),
            gold_writer=GoldWriter(
                base_path=gold_base_path,
                storage_options=storage_options,
                csv_exporter=gold_csv_exporter,
            ),
        )

        return StorageContext(
            adapter=adapter,
            bronze_path=bronze_path,
            silver_path=silver_base_path,
            gold_path=gold_base_path,
            checkpoints_path=checkpoints_path,
        )
