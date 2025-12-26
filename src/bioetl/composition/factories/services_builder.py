"""Services builder for pipeline components.

Provides helper functions for creating pipeline infrastructure components
like CheckpointManager and RecordProcessor.

Extracted from generic_factory.py for better separation of concerns.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.checkpoint_manager import CheckpointManager
from bioetl.application.core.config import RecordProcessorConfig
from bioetl.application.core.record_processor import RecordProcessor
from bioetl.domain.config import TableConfig
from bioetl.domain.error_classifier import ErrorClassifier
from bioetl.infrastructure.validation import PanderaGoldValidator

if TYPE_CHECKING:
    import pyarrow as pa
    import structlog

    from bioetl.application.core.base import BasePipeline
    from bioetl.application.core.pipeline_context import PipelineContext
    from bioetl.application.core.pipeline_services import PipelineServices
    from bioetl.domain.ports import CheckpointPort
    from bioetl.domain.types import RunID


class ServicesBuilder:
    """Builder for pipeline infrastructure components."""

    @staticmethod
    def create_checkpoint_manager(
        checkpoint_port: CheckpointPort,
        logger: structlog.BoundLogger,
        pipeline_name: str,
        run_id: RunID,
        resume: bool,
    ) -> CheckpointManager:
        """Create configured CheckpointManager.

        Args:
            checkpoint_port: Checkpoint storage port
            logger: Structured logger
            pipeline_name: Name of the pipeline
            run_id: Unique run identifier
            resume: Whether to resume from previous checkpoint

        Returns:
            Configured CheckpointManager instance
        """
        return CheckpointManager(
            checkpoint_port=checkpoint_port,
            logger=logger,
            pipeline_name=pipeline_name,
            run_id=run_id,
            resume=resume,
        )

    @staticmethod
    def create_record_processor(
        services: PipelineServices,
        context: PipelineContext,
        pipeline_name: str,
        provider: str,
        entity_type: str,
        silver_schema: pa.Schema | None,
        gold_schema: Any,
        dq_config: Any,
        primary_keys: list[str],
        silver_table: str,
        gold_table: str,
        silver_write_mode: str,
        gold_write_mode: str,
        on_schema_mismatch: str,
        transform_callback: Any,
        gold_filter_callback: Any,
        gold_transform_callback: Any,
    ) -> RecordProcessor:
        """Create configured RecordProcessor.

        Args:
            services: Pipeline services
            context: Pipeline context
            pipeline_name: Name of the pipeline
            provider: Data provider name
            entity_type: Entity type being processed
            silver_schema: PyArrow schema for Silver layer
            gold_schema: Pandera schema for Gold layer
            dq_config: Data quality configuration
            primary_keys: Primary key fields
            silver_table: Silver table name
            gold_table: Gold table name
            silver_write_mode: Write mode for Silver
            gold_write_mode: Write mode for Gold
            on_schema_mismatch: Schema mismatch handling strategy
            transform_callback: Bronze to Silver transformation callback
            gold_filter_callback: Gold filtering callback
            gold_transform_callback: Silver to Gold transformation callback

        Returns:
            Configured RecordProcessor instance
        """
        error_classifier = ErrorClassifier()
        table_config = TableConfig(
            primary_keys=primary_keys,
            silver_table=silver_table,
            gold_table=gold_table,
            silver_write_mode=silver_write_mode,
            gold_write_mode=gold_write_mode,
            on_schema_mismatch=on_schema_mismatch,
        )

        processor_config = RecordProcessorConfig(
            pipeline_name=pipeline_name,
            provider=provider,
            entity_type=entity_type,
            silver_schema=silver_schema,
            gold_schema=gold_schema,
            dq_config=dq_config,
            table_config=table_config,
        )

        # Create Gold validator from schema (DI pattern)
        gold_validator = PanderaGoldValidator(gold_schema)

        return RecordProcessor(
            services=services,
            error_classifier=error_classifier,
            context=context,
            config=processor_config,
            transform_callback=transform_callback,
            gold_filter_callback=gold_filter_callback,
            gold_transform_callback=gold_transform_callback,
            gold_validator=gold_validator,
        )

    @staticmethod
    def create_record_processor_from_pipeline(
        pipeline: BasePipeline,
        silver_schema: pa.Schema | None,
        gold_schema: Any,
    ) -> RecordProcessor:
        """Create RecordProcessor from pipeline instance.

        Convenience method that extracts configuration from pipeline.

        Args:
            pipeline: Pipeline instance
            silver_schema: PyArrow schema for Silver layer
            gold_schema: Pandera schema for Gold layer

        Returns:
            Configured RecordProcessor instance
        """
        return ServicesBuilder.create_record_processor(
            services=pipeline.services,
            context=pipeline.context,
            pipeline_name=pipeline.config.pipeline_name,
            provider=pipeline.config.provider,
            entity_type=pipeline.config.entity_type,
            silver_schema=silver_schema,
            gold_schema=gold_schema,
            dq_config=pipeline.config.dq,
            primary_keys=pipeline.config.primary_keys,
            silver_table=pipeline.config.silver_table,
            gold_table=pipeline.config.gold_table,
            silver_write_mode=pipeline.config.write_mode,
            gold_write_mode=pipeline.config.gold_write_mode,
            on_schema_mismatch=pipeline.config.on_schema_mismatch,
            transform_callback=pipeline.transform_bronze_to_silver,
            gold_filter_callback=pipeline.should_write_gold,
            gold_transform_callback=pipeline.transform_for_gold,
        )
