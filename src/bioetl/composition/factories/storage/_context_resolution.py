"""Context and path resolution helpers for StorageFactory assembly flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.infrastructure.export.csv_exporter import CsvExporter

if TYPE_CHECKING:
    from bioetl.domain.ports import LoggerPort
    from bioetl.infrastructure.config._base import Settings
    from bioetl.infrastructure.schemas.pipeline_config import (
        PipelineYamlConfig,
        SinkLayerConfig,
    )


@dataclass(frozen=True, slots=True)
class StorageCreationContext:
    """Resolved per-layer configuration for storage adapter creation (RF-005a)."""

    bronze_config: SinkLayerConfig | None
    silver_config: SinkLayerConfig | None
    gold_config: SinkLayerConfig | None
    bronze_path: Path
    silver_path: Path
    gold_path: Path
    bronze_flat: bool
    silver_flat: bool
    gold_flat: bool
    silver_csv_exporter: CsvExporter | None
    gold_csv_exporter: CsvExporter | None
    pipeline_name: str


def create_csv_exporter_from_config(
    csv_cfg: object | None,
    logger: LoggerPort,
    override_path: Path | None = None,
) -> CsvExporter | None:
    """Create CsvExporter from config, or None if disabled/unconfigured."""
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


def resolve_layer_path(
    layer_config: SinkLayerConfig | None,
    default_path: Path,
    use_yaml_paths: bool,
) -> Path:
    """Resolve storage path from sink config or fall back to default."""
    if use_yaml_paths and layer_config and layer_config.path:
        return Path(layer_config.path)
    return default_path


def get_layer_configs(
    config: PipelineYamlConfig,
) -> tuple[SinkLayerConfig | None, SinkLayerConfig | None, SinkLayerConfig | None]:
    """Extract per-layer sink configs: (bronze, silver, gold), each may be None."""
    return config.sink.get("bronze"), config.sink.get("silver"), config.sink.get("gold")


def resolve_storage_paths(
    settings: Settings,
    bronze_config: SinkLayerConfig | None,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
) -> tuple[bool, Path, Path, Path]:
    """Resolve storage paths; returns (use_yaml_paths, bronze, silver, gold)."""
    use_yaml_paths = not settings.test_mode
    return (
        use_yaml_paths,
        resolve_layer_path(bronze_config, settings.bronze_path, use_yaml_paths),
        resolve_layer_path(silver_config, settings.silver_path, use_yaml_paths),
        resolve_layer_path(gold_config, settings.gold_path, use_yaml_paths),
    )


def create_layer_exporters(
    *,
    settings: Settings,
    logger: LoggerPort,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
    silver_path: Path,
    gold_path: Path,
) -> tuple[CsvExporter | None, CsvExporter | None]:
    """Create optional CSV exporters for Silver and Gold layers."""
    override = silver_path if settings.test_mode else None
    silver_csv = create_csv_exporter_from_config(
        silver_config.csv_export if silver_config else None, logger, override
    )
    override = gold_path if settings.test_mode else None
    gold_csv = create_csv_exporter_from_config(
        gold_config.csv_export if gold_config else None, logger, override
    )
    return silver_csv, gold_csv


def resolve_export_flags(
    bronze_config: SinkLayerConfig | None,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
) -> tuple[bool, bool, bool, bool]:
    """Resolve (save_json, bronze_meta, silver_meta, gold_meta) flags."""
    return (
        bronze_config.save_json if bronze_config else False,
        bronze_config.save_metadata if bronze_config else False,
        silver_config.save_metadata if silver_config else False,
        gold_config.save_metadata if gold_config else False,
    )


def log_export_status(
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


def log_configured_export_status(
    *,
    logger: LoggerPort,
    bronze_config: SinkLayerConfig | None,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
    silver_csv_exporter: CsvExporter | None,
    gold_csv_exporter: CsvExporter | None,
) -> None:
    """Resolve and log export settings for configured layers."""
    save_json, bronze_save_metadata, silver_save_metadata, gold_save_metadata = (
        resolve_export_flags(bronze_config, silver_config, gold_config)
    )
    log_export_status(
        logger,
        save_json,
        silver_csv_exporter,
        gold_csv_exporter,
        bronze_save_metadata,
        silver_save_metadata,
        gold_save_metadata,
    )


def resolve_flat_structure_flags(
    *,
    bronze_config: SinkLayerConfig | None,
    silver_config: SinkLayerConfig | None,
    gold_config: SinkLayerConfig | None,
    use_yaml_paths: bool,
) -> tuple[bool, bool, bool]:
    """Resolve (bronze, silver, gold) flat-structure flags."""
    return (
        (bronze_config.flat_structure if bronze_config else False) and use_yaml_paths,
        (silver_config.flat_structure if silver_config else False) and use_yaml_paths,
        (gold_config.flat_structure if gold_config else False) and use_yaml_paths,
    )


def build_storage_creation_context(
    *,
    settings: Settings,
    config: PipelineYamlConfig,
    logger: LoggerPort,
    pipeline_name: str,
) -> StorageCreationContext:
    """Run the full layer-resolution pipeline and return a bundled context."""
    bronze_config, silver_config, gold_config = get_layer_configs(config)
    use_yaml_paths, bronze_path, silver_path, gold_path = resolve_storage_paths(
        settings=settings,
        bronze_config=bronze_config,
        silver_config=silver_config,
        gold_config=gold_config,
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
    bronze_flat, silver_flat, gold_flat = resolve_flat_structure_flags(
        bronze_config=bronze_config,
        silver_config=silver_config,
        gold_config=gold_config,
        use_yaml_paths=use_yaml_paths,
    )
    return StorageCreationContext(
        bronze_config=bronze_config,
        silver_config=silver_config,
        gold_config=gold_config,
        bronze_path=bronze_path,
        silver_path=silver_path,
        gold_path=gold_path,
        bronze_flat=bronze_flat,
        silver_flat=silver_flat,
        gold_flat=gold_flat,
        silver_csv_exporter=silver_csv_exporter,
        gold_csv_exporter=gold_csv_exporter,
        pipeline_name=pipeline_name,
    )
