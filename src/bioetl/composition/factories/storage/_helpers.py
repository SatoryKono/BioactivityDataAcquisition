"""Helper functions for StorageFactory assembly flow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.infrastructure.export.csv_exporter import CsvExporter

from ._bronze import create_bronze_writer
from ._gold import create_gold_writer
from ._resilience import (
    create_silver_atomic_retry_policy,
    create_silver_merge_resilience_policy,
)
from ._silver import create_silver_writer
from .adapter import StorageAdapter

if TYPE_CHECKING:
    from bioetl.application.services.metadata_coordinator import MetadataCoordinator
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
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter


@dataclass(frozen=True, slots=True)
class StorageCreationContext:
    """Resolved per-layer configuration for storage adapter creation (RF-005a).

    Bundles all layer configs, paths, flat-structure flags and CSV exporters
    produced by the resolution pipeline (steps 1-4 of StorageFactory.create).
    """

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


def _has_provider_entity_suffix(
    path: Path,
    *,
    provider: str,
    entity_type: str,
) -> bool:
    """Return True when a path already ends with provider/entity segments."""
    parts = Path(str(path).replace("\\", "/")).parts
    if len(parts) < 2:
        return False
    return parts[-2:] == (provider, entity_type)


def resolve_delta_writer_base_path(
    resolved_path: Path,
    *,
    provider: str,
    entity_type: str,
    flat_structure: bool,
) -> Path:
    """Normalize Delta writer base_path to the layer root when path is entity-scoped.

    Storage contexts still expose the fully resolved per-pipeline target path for
    observability and report generation. Delta writers, however, must keep a
    layer-root base path so downstream maintenance helpers can append the logical
    table id exactly once.
    """
    runtime_path = Path(str(resolved_path).replace("\\", "/"))
    if flat_structure:
        return runtime_path
    if _has_provider_entity_suffix(
        runtime_path,
        provider=provider,
        entity_type=entity_type,
    ):
        return runtime_path.parent.parent
    return runtime_path


def resolve_delta_writer_flat_structure(
    resolved_path: Path,
    *,
    provider: str,
    entity_type: str,
    flat_structure: bool,
) -> bool:
    """Downgrade entity-scoped flat Delta paths to layer-root/table-name mode.

    When configuration normalization already materializes a path like
    ``data/output/silver/provider/entity``, keeping ``flat_structure=True`` would
    collapse all Delta writes onto that single directory and break maintenance
    helpers that work with logical table ids. In that case we switch writers back
    to the canonical layer-root + logical-table contract.
    """
    if not flat_structure:
        return False
    return not _has_provider_entity_suffix(
        resolved_path,
        provider=provider,
        entity_type=entity_type,
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
) -> StorageCreationContext:
    """Run the full layer-resolution pipeline and return a bundled context.

    Resolves layer configs, storage paths, CSV exporters, flat-structure
    flags, and logs export status — encapsulating steps 1-4 of the
    StorageFactory.create flow into a single parameter object.
    """
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
    )


def create_storage_adapter(
    *,
    ctx: StorageCreationContext,
    bronze_writer_cls: type[BronzeWriter],
    silver_writer_cls: type[SilverWriter],
    gold_writer_cls: type[GoldWriter],
    settings: Settings,
    config: PipelineYamlConfig,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracing: TracingPort | None,
    metadata_coordinator: MetadataCoordinator | None,
    silver_validator: SilverValidatorPort | None,
) -> StorageAdapter:
    """Create StorageAdapter with Bronze/Silver/Gold writers."""
    metadata_atomic_retry_policy = create_silver_atomic_retry_policy(settings)
    merge_resilience_policy = create_silver_merge_resilience_policy(settings)
    silver_writer_flat = resolve_delta_writer_flat_structure(
        ctx.silver_path,
        provider=config.provider,
        entity_type=config.entity_type,
        flat_structure=ctx.silver_flat,
    )
    gold_writer_flat = resolve_delta_writer_flat_structure(
        ctx.gold_path,
        provider=config.provider,
        entity_type=config.entity_type,
        flat_structure=ctx.gold_flat,
    )

    bronze_writer = create_bronze_writer(
        writer_cls=bronze_writer_cls,
        base_path=ctx.bronze_path,
        config=ctx.bronze_config,
        logger=logger,
        metrics=metrics,
        tracing=tracing,
        metadata_coordinator=metadata_coordinator,
        flat_structure=ctx.bronze_flat,
    )
    silver_writer = create_silver_writer(
        writer_cls=silver_writer_cls,
        base_path=resolve_delta_writer_base_path(
            ctx.silver_path,
            provider=config.provider,
            entity_type=config.entity_type,
            flat_structure=silver_writer_flat,
        ),
        config=ctx.silver_config,
        logger=logger,
        tracing=tracing,
        csv_exporter=ctx.silver_csv_exporter,
        metadata_coordinator=metadata_coordinator,
        transform_version=config.transform.version,
        transform_steps=tuple(config.transform.steps),
        flat_structure=silver_writer_flat,
        silver_validator=silver_validator,
        metrics=metrics,
        metadata_atomic_retry_policy=metadata_atomic_retry_policy,
        merge_resilience_policy=merge_resilience_policy,
    )
    gold_writer = create_gold_writer(
        writer_cls=gold_writer_cls,
        base_path=resolve_delta_writer_base_path(
            ctx.gold_path,
            provider=config.provider,
            entity_type=config.entity_type,
            flat_structure=gold_writer_flat,
        ),
        config=ctx.gold_config,
        logger=logger,
        tracing=tracing,
        csv_exporter=ctx.gold_csv_exporter,
        metadata_coordinator=metadata_coordinator,
        transform_version=config.transform.version,
        transform_steps=tuple(config.transform.steps),
        flat_structure=gold_writer_flat,
        metrics=metrics,
    )
    return StorageAdapter(
        bronze_writer=bronze_writer,
        silver_writer=silver_writer,
        gold_writer=gold_writer,
    )
