from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bioetl.infrastructure.config import Settings
from bioetl.infrastructure.factories.clients import get_aws_credentials
from bioetl.infrastructure.factories.storage import StorageAdapter
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.delta_writer import DeltaWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter

if TYPE_CHECKING:
    import structlog


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
        logger: "structlog.BoundLogger",
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
        silver_csv_path = None
        silver_csv_options = None
        gold_csv_path = None
        gold_csv_options = None

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
                silver_csv_path = csv_cfg.path
                silver_csv_options = {
                    "delimiter": csv_cfg.delimiter,
                    "header": csv_cfg.header,
                    "encoding": csv_cfg.encoding,
                }

            # Handle CSV export (Gold)
            if gold_config and gold_config.csv_export.enabled:
                csv_cfg = gold_config.csv_export
                gold_csv_path = csv_cfg.path
                gold_csv_options = {
                    "delimiter": csv_cfg.delimiter,
                    "header": csv_cfg.header,
                    "encoding": csv_cfg.encoding,
                }
        else:
            # Cloud paths
            bronze_path = s3_config.bucket_bronze
            silver_base_path = f"s3://{s3_config.bucket_silver}"
            gold_base_path = f"s3://{s3_config.bucket_gold}"
            checkpoints_path = s3_config.bucket_checkpoints

        # Logging
        if json_path:
            logger.info("JSON export enabled for Bronze layer")
        if silver_csv_path:
            logger.info(f"CSV export enabled for Silver layer: {silver_csv_path}")
        if gold_csv_path:
            logger.info(f"CSV export enabled for Gold layer: {gold_csv_path}")

        # Determine save_json flag
        save_json = bronze_config.save_json if bronze_config else False

        adapter = StorageAdapter(
            bronze=BronzeWriter(
                bucket=bronze_path,
                endpoint_url=aws_config.endpoint_url if not is_local_run else None,
                access_key=access_key,
                secret_key=secret_key,
                save_json=save_json,
                json_path=json_path,
                logger=logger,
            ),
            silver=DeltaWriter(
                base_path=silver_base_path,
                storage_options=storage_options,
                csv_path=silver_csv_path,
                csv_options=silver_csv_options,
            ),
            gold=GoldWriter(
                base_path=gold_base_path,
                storage_options=storage_options,
                csv_path=gold_csv_path,
                csv_options=gold_csv_options,
            ),
        )

        return StorageContext(
            adapter=adapter,
            bronze_path=bronze_path,
            silver_path=silver_base_path,
            gold_path=gold_base_path,
            checkpoints_path=checkpoints_path,
        )
