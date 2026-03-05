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

from bioetl.domain.ports import NoOpMetadataWriter, NoOpTracing
from bioetl.infrastructure.export.csv_exporter import CsvExporter
from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
from bioetl.infrastructure.storage.gold_writer import GoldWriter
from bioetl.infrastructure.storage.metadata_writer import MetadataWriter
from bioetl.infrastructure.storage.silver_writer import SilverWriter

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
class _StorageBuildInputs:
    """Resolved inputs required to build a storage context."""

    bronze_config: SinkLayerConfig | None
    silver_config: SinkLayerConfig | None
    gold_config: SinkLayerConfig | None
    bronze_path: Path
    silver_path: Path
    gold_path: Path
    transform_version: str | None
    transform_steps: tuple[str, ...]
    bronze_flat_structure: bool
    silver_flat_structure: bool
    gold_flat_structure: bool
    silver_csv_exporter: CsvExporter | None
    gold_csv_exporter: CsvExporter | None


def _resolve_layer_configs(
    config: PipelineYamlConfig,
) -> tuple[SinkLayerConfig | None, SinkLayerConfig | None, SinkLayerConfig | None]:
    """Resolve Bronze/Silver/Gold sink layer configs from pipeline config."""
    bronze_config = config.sink.get("bronze")
    silver_config = config.sink.get("silver")
    gold_config = config.sink.get("gold")
    return bronze_config, silver_config, gold_config


def _resolve_storage_paths(
    *,
    settings: Settings,
    bronze_config: SinkLayerConfig | None,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
) -> tuple[Path, Path, Path, bool]:
    """Resolve effective layer paths and whether YAML paths are enabled."""
    use_yaml_paths = not settings.test_mode
    bronze_path = StorageFactory._resolve_layer_path(
        bronze_config,
        settings.bronze_path,
        use_yaml_paths,
    )
    silver_path = StorageFactory._resolve_layer_path(
        silver_config,
        settings.silver_path,
        use_yaml_paths,
    )
    gold_path = StorageFactory._resolve_layer_path(
        gold_config,
        settings.gold_path,
        use_yaml_paths,
    )
    return bronze_path, silver_path, gold_path, use_yaml_paths


def _create_csv_exporters(
    *,
    settings: Settings,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
    logger: LoggerPort,
    silver_path: Path,
    gold_path: Path,
) -> tuple[CsvExporter | None, CsvExporter | None]:
    """Create optional CSV exporters for Silver and Gold layers."""
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
    return silver_csv_exporter, gold_csv_exporter


def _resolve_metadata_flags(
    *,
    bronze_config: SinkLayerConfig | None,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
) -> tuple[bool, bool, bool, bool]:
    """Resolve JSON/metadata export flags from sink-layer configs."""
    save_json = bronze_config.save_json if bronze_config else False
    bronze_save_metadata = bronze_config.save_metadata if bronze_config else False
    silver_save_metadata = silver_config.save_metadata if silver_config else False
    gold_save_metadata = gold_config.save_metadata if gold_config else False
    return save_json, bronze_save_metadata, silver_save_metadata, gold_save_metadata


def _resolve_flat_structure_flags(
    *,
    bronze_config: SinkLayerConfig | None,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
    use_yaml_paths: bool,
) -> tuple[bool, bool, bool]:
    """Resolve flat-structure flags with test-mode safety."""
    bronze_flat_structure = (
        bronze_config.flat_structure if bronze_config else False
    ) and use_yaml_paths
    silver_flat_structure = (
        silver_config.flat_structure if silver_config else False
    ) and use_yaml_paths
    gold_flat_structure = (gold_config.flat_structure if gold_config else False) and (
        use_yaml_paths
    )
    return bronze_flat_structure, silver_flat_structure, gold_flat_structure


def _log_storage_paths(
    *,
    logger: LoggerPort,
    bronze_path: Path,
    silver_path: Path,
    gold_path: Path,
) -> None:
    """Log resolved Bronze/Silver/Gold storage paths."""
    logger.info(
        "Using local storage",
        bronze_path=str(bronze_path),
        silver_path=str(silver_path),
        gold_path=str(gold_path),
    )


def _resolve_exporters_with_logging(
    *,
    settings: Settings,
    bronze_config: SinkLayerConfig | None,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
    logger: LoggerPort,
    silver_path: Path,
    gold_path: Path,
) -> tuple[CsvExporter | None, CsvExporter | None]:
    """Create exporters and emit export-status telemetry."""
    silver_csv_exporter, gold_csv_exporter = _create_csv_exporters(
        settings=settings,
        silver_config=silver_config,
        gold_config=gold_config,
        logger=logger,
        silver_path=silver_path,
        gold_path=gold_path,
    )
    save_json, bronze_save_metadata, silver_save_metadata, gold_save_metadata = (
        _resolve_metadata_flags(
            bronze_config=bronze_config,
            silver_config=silver_config,
            gold_config=gold_config,
        )
    )
    StorageFactory._log_export_status(
        logger,
        save_json,
        silver_csv_exporter,
        gold_csv_exporter,
        bronze_save_metadata,
        silver_save_metadata,
        gold_save_metadata,
    )
    return silver_csv_exporter, gold_csv_exporter


def _resolve_transform_and_flat(
    *,
    config: PipelineYamlConfig,
    bronze_config: SinkLayerConfig | None,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
    use_yaml_paths: bool,
) -> tuple[str | None, tuple[str, ...], bool, bool, bool]:
    """Resolve transform lineage info and flat-structure flags."""
    bronze_flat_structure, silver_flat_structure, gold_flat_structure = (
        _resolve_flat_structure_flags(
            bronze_config=bronze_config,
            silver_config=silver_config,
            gold_config=gold_config,
            use_yaml_paths=use_yaml_paths,
        )
    )
    return (
        config.transform.version,
        tuple(config.transform.steps),
        bronze_flat_structure,
        silver_flat_structure,
        gold_flat_structure,
    )


def _pack_storage_build_inputs(
    *,
    bronze_config: SinkLayerConfig | None,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
    bronze_path: Path,
    silver_path: Path,
    gold_path: Path,
    transform_version: str | None,
    transform_steps: tuple[str, ...],
    bronze_flat_structure: bool,
    silver_flat_structure: bool,
    gold_flat_structure: bool,
    silver_csv_exporter: CsvExporter | None,
    gold_csv_exporter: CsvExporter | None,
) -> _StorageBuildInputs:
    """Pack resolved storage inputs into immutable transfer object."""
    return _StorageBuildInputs(
        bronze_config=bronze_config,
        silver_config=silver_config,
        gold_config=gold_config,
        bronze_path=bronze_path,
        silver_path=silver_path,
        gold_path=gold_path,
        transform_version=transform_version,
        transform_steps=transform_steps,
        bronze_flat_structure=bronze_flat_structure,
        silver_flat_structure=silver_flat_structure,
        gold_flat_structure=gold_flat_structure,
        silver_csv_exporter=silver_csv_exporter,
        gold_csv_exporter=gold_csv_exporter,
    )


def _assemble_storage_build_inputs(
    *,
    config: PipelineYamlConfig,
    bronze_config: SinkLayerConfig | None,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
    bronze_path: Path,
    silver_path: Path,
    gold_path: Path,
    use_yaml_paths: bool,
    silver_csv_exporter: CsvExporter | None,
    gold_csv_exporter: CsvExporter | None,
) -> _StorageBuildInputs:
    """Assemble full immutable build input payload."""
    (
        transform_version,
        transform_steps,
        bronze_flat_structure,
        silver_flat_structure,
        gold_flat_structure,
    ) = _resolve_transform_and_flat(
        config=config,
        bronze_config=bronze_config,
        silver_config=silver_config,
        gold_config=gold_config,
        use_yaml_paths=use_yaml_paths,
    )
    return _pack_storage_build_inputs(
        bronze_config=bronze_config,
        silver_config=silver_config,
        gold_config=gold_config,
        bronze_path=bronze_path,
        silver_path=silver_path,
        gold_path=gold_path,
        transform_version=transform_version,
        transform_steps=transform_steps,
        bronze_flat_structure=bronze_flat_structure,
        silver_flat_structure=silver_flat_structure,
        gold_flat_structure=gold_flat_structure,
        silver_csv_exporter=silver_csv_exporter,
        gold_csv_exporter=gold_csv_exporter,
    )


def _build_storage_context(
    *,
    settings: Settings,
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
) -> StorageContext:
    """Build storage adapter and wrap it with resolved storage paths."""
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


def _resolve_storage_build_inputs(
    *,
    settings: Settings,
    config: PipelineYamlConfig,
    logger: LoggerPort,
) -> _StorageBuildInputs:
    """Resolve storage paths/export options required for adapter creation."""
    bronze_config, silver_config, gold_config = _resolve_layer_configs(config)
    bronze_path, silver_path, gold_path, use_yaml_paths = _resolve_storage_paths(
        settings=settings,
        bronze_config=bronze_config,
        silver_config=silver_config,
        gold_config=gold_config,
    )
    _log_storage_paths(
        logger=logger,
        bronze_path=bronze_path,
        silver_path=silver_path,
        gold_path=gold_path,
    )
    silver_csv_exporter, gold_csv_exporter = _resolve_exporters_with_logging(
        settings=settings,
        bronze_config=bronze_config,
        silver_config=silver_config,
        gold_config=gold_config,
        logger=logger,
        silver_path=silver_path,
        gold_path=gold_path,
    )
    return _assemble_storage_build_inputs(
        config=config,
        bronze_config=bronze_config,
        silver_config=silver_config,
        gold_config=gold_config,
        bronze_path=bronze_path,
        silver_path=silver_path,
        gold_path=gold_path,
        use_yaml_paths=use_yaml_paths,
        silver_csv_exporter=silver_csv_exporter,
        gold_csv_exporter=gold_csv_exporter,
    )


def _create_context_with_resolved_inputs(
    *,
    settings: Settings,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracing: TracingPort | None,
    metadata_coordinator: MetadataCoordinator | None,
    silver_validator: SilverValidatorPort | None,
    build_inputs: _StorageBuildInputs,
) -> StorageContext:
    """Create storage context from pre-resolved build inputs."""
    return _build_storage_context(
        settings=settings,
        bronze_path=build_inputs.bronze_path,
        silver_path=build_inputs.silver_path,
        gold_path=build_inputs.gold_path,
        bronze_config=build_inputs.bronze_config,
        silver_config=build_inputs.silver_config,
        gold_config=build_inputs.gold_config,
        silver_csv_exporter=build_inputs.silver_csv_exporter,
        gold_csv_exporter=build_inputs.gold_csv_exporter,
        logger=logger,
        metrics=metrics,
        tracing=tracing,
        metadata_coordinator=metadata_coordinator,
        transform_version=build_inputs.transform_version,
        transform_steps=build_inputs.transform_steps,
        bronze_flat_structure=build_inputs.bronze_flat_structure,
        silver_flat_structure=build_inputs.silver_flat_structure,
        gold_flat_structure=build_inputs.gold_flat_structure,
        silver_validator=silver_validator,
    )


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
        csv_cfg: object | None,
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
        if csv_cfg and getattr(csv_cfg, "enabled", False):
            # Convert to str for CsvExporter (expects str, not Path)
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
        return None

    @staticmethod
    def _resolve_layer_path(
        layer_config: SinkLayerConfig | None,
        default_path: Path,
        use_yaml_paths: bool,
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
        bronze_config: SinkLayerConfig | None,
        silver_config: SinkLayerConfig | None,
        gold_config: SinkLayerConfig | None,
        silver_csv_exporter: CsvExporter | None,
        gold_csv_exporter: CsvExporter | None,
        logger: LoggerPort,
        metrics: MetricsPort,
        tracing: TracingPort | None,
        metadata_coordinator: MetadataCoordinator | None = None,
        transform_version: str | None = None,
        transform_steps: tuple[str, ...] | None = None,
        bronze_flat_structure: bool = False,
        silver_flat_structure: bool = False,
        gold_flat_structure: bool = False,
        silver_validator: SilverValidatorPort | None = None,
    ) -> StorageAdapter:
        """Create StorageAdapter with all writers configured.

        Instantiates BronzeWriter, SilverWriter, and GoldWriter with the
        provided paths, configs, and observability ports, then composes
        them into a unified StorageAdapter.

        Args:
            bronze_path: Base filesystem path for Bronze layer output.
            silver_path: Base filesystem path for Silver layer Delta tables.
            gold_path: Base filesystem path for Gold layer Delta tables.
            bronze_config: Pydantic sink config for Bronze layer (save_json,
                save_metadata, flat_structure settings).
            silver_config: Pydantic sink config for Silver layer (save_metadata,
                flat_structure settings).
            gold_config: Pydantic sink config for Gold layer (save_metadata,
                flat_structure settings).
            silver_csv_exporter: Optional CsvExporter for Silver layer CSV output.
            gold_csv_exporter: Optional CsvExporter for Gold layer CSV output.
            logger: Structured logger for all writer observability.
            metrics: Metrics port for Bronze write observability.
            tracing: Optional TracingPort for distributed tracing. Falls back
                to NoOpTracing if None.
            metadata_coordinator: Optional MetadataCoordinator for centralized
                metadata creation across all layers with consistent run_id
                and timestamps.
            transform_version: Optional version string for lineage tracking
                in Silver and Gold metadata.
            transform_steps: Optional tuple of transform step names for
                lineage tracking in Silver and Gold metadata.
            bronze_flat_structure: If True, Bronze writes directly to base_path
                without provider/entity subdirectories.
            silver_flat_structure: If True, Silver writes directly to base_path
                without table_name subdirectories.
            gold_flat_structure: If True, Gold writes directly to base_path
                without table_name subdirectories.
            silver_validator: Optional SilverValidatorPort for Pandera validation
                in SilverWriter. If None, validation is skipped.

        Returns:
            Configured StorageAdapter with Bronze, Silver, and Gold writers.

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
                flat_structure=bronze_flat_structure,
            ),
            silver_writer=SilverWriter(
                base_path=silver_path,
                logger=logger,
                tracing=effective_tracing,
                csv_exporter=silver_csv_exporter,
                silver_validator=silver_validator,
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
        silver_validator: SilverValidatorPort | None = None,
    ) -> StorageContext:
        """Create local storage context with configured layer writers."""
        build_inputs = _resolve_storage_build_inputs(
            settings=settings,
            config=config,
            logger=logger,
        )
        return _create_context_with_resolved_inputs(
            settings=settings,
            logger=logger,
            metrics=metrics,
            tracing=tracing,
            metadata_coordinator=metadata_coordinator,
            silver_validator=silver_validator,
            build_inputs=build_inputs,
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
