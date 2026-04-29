"""StorageFactory - thin facade for creating StorageBundles."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.application.services.lineage.metadata_coordinator import MetadataCoordinator
from bioetl.composition.observability_resolution import resolve_tracing_port
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

from ._helpers import (
    build_storage_creation_context,
    create_storage_adapter,
)
from .adapter import StorageBundle

if TYPE_CHECKING:
    from bioetl.domain.ports import (
        AuditPort,
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

__all__ = [
    "BronzeWriter",
    "GoldWriter",
    "SilverWriter",
    "StorageContext",
    "StorageFactory",
]


@dataclass(frozen=True)
class StorageContext:
    """Context object returned by StorageFactory containing adapter and paths."""

    adapter: StorageBundle
    bronze_path: Path
    silver_path: Path
    gold_path: Path
    checkpoints_path: Path


class StorageFactory:
    """Factory for creating configured StorageBundles for local deployment."""

    @staticmethod
    def create(
        settings: Settings,
        config: PipelineYamlConfig,
        logger: LoggerPort,
        metrics: MetricsPort,
        audit: AuditPort,
        tracing: TracingPort | None = None,
        metadata_coordinator: MetadataCoordinator | None = None,
        silver_validator: SilverValidatorPort | None = None,
        pipeline_name: str | None = None,
    ) -> StorageContext:
        """Create local storage context with configured layer writers.

        Args:
            settings: Application settings providing base paths, test_mode, and
                resilience configuration.
            config: Pipeline YAML configuration with sink layer definitions.
            logger: LoggerPort for structured logging and export status events.
            metrics: MetricsPort for storage metrics collection.
            audit: Canonical runtime audit port shared across storage and runner lifecycle.
            tracing: Optional TracingPort. When omitted, composition resolves an
                explicit NoOpTracing for the layer writers.
            metadata_coordinator: Optional coordinator for metadata side-effects;
                defaults to None.
            silver_validator: Optional PyArrow schema validator for Silver records;
                defaults to None.

        Returns:
            StorageContext with assembled adapter and resolved layer paths.
        """
        ctx = build_storage_creation_context(
            settings=settings,
            config=config,
            logger=logger,
            pipeline_name=(
                pipeline_name
                or getattr(config, "pipeline_name", None)
                or f"{config.provider}_{config.entity_type}"
            ),
        )
        logger.info(
            "Using local storage",
            bronze_path=str(ctx.bronze_path),
            silver_path=str(ctx.silver_path),
            gold_path=str(ctx.gold_path),
        )
        resolved_tracing = resolve_tracing_port(tracer=tracing, settings=settings)
        adapter = create_storage_adapter(
            ctx=ctx,
            bronze_writer_cls=BronzeWriter,
            silver_writer_cls=SilverWriter,
            gold_writer_cls=GoldWriter,
            settings=settings,
            config=config,
            logger=logger,
            metrics=metrics,
            tracing=resolved_tracing,
            audit=audit,
            metadata_coordinator=metadata_coordinator,
            silver_validator=silver_validator,
        )
        return StorageContext(
            adapter=adapter,
            bronze_path=ctx.bronze_path,
            silver_path=ctx.silver_path,
            gold_path=ctx.gold_path,
            checkpoints_path=settings.checkpoint_path,
        )
