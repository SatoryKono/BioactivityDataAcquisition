"""Helper functions for StorageFactory assembly flow."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bioetl.infrastructure.config.contract_policy_loader import (
    load_pipeline_contract_policy as _load_pipeline_contract_policy,
)

from ._bronze import create_bronze_writer
from ._context_resolution import (
    StorageCreationContext,
    build_storage_creation_context,
    create_csv_exporter_from_config,
    create_layer_exporters,
    get_layer_configs,
    log_configured_export_status,
    log_export_status,
    resolve_export_flags,
    resolve_flat_structure_flags,
    resolve_layer_path,
    resolve_storage_paths,
)
from ._layer_writers import (
    _SilverLayerWriterSupport,
    create_gold_layer_writer_impl,
    create_silver_layer_writer_impl,
)
from ._resilience import (
    create_silver_atomic_retry_policy,
    create_silver_merge_resilience_policy,
)
from .adapter import StorageAdapter

if TYPE_CHECKING:
    from bioetl.application.services.lineage.metadata_coordinator import (
        MetadataCoordinator,
    )
    from bioetl.domain.ports import (
        AuditPort,
        LoggerPort,
        MetricsPort,
        SilverValidatorPort,
        TracingPort,
    )
    from bioetl.domain.types.contract_rollout import ContractRolloutPolicy
    from bioetl.infrastructure.config import Settings
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
    from bioetl.infrastructure.storage.bronze_writer import BronzeWriter
    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

__all__ = [
    "StorageCreationContext",
    "build_storage_creation_context",
    "create_csv_exporter_from_config",
    "create_layer_exporters",
    "create_storage_adapter",
    "get_layer_configs",
    "load_contract_rollout_policy",
    "load_pipeline_contract_policy",
    "log_configured_export_status",
    "log_export_status",
    "resolve_delta_writer_base_path",
    "resolve_delta_writer_flat_structure",
    "resolve_export_flags",
    "resolve_flat_structure_flags",
    "resolve_layer_path",
    "resolve_storage_paths",
]


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


def load_pipeline_contract_policy(provider: str, entity: str):
    """Return the pipeline contract policy loader used by storage assembly."""
    return _load_pipeline_contract_policy(provider, entity)


def load_contract_rollout_policy(config: PipelineYamlConfig) -> ContractRolloutPolicy:
    """Adapt pipeline contract policy into the writer-facing rollout DTO."""
    return load_pipeline_contract_policy(
        config.provider,
        config.entity_type,
    ).to_contract_rollout_policy()


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
    tracing: TracingPort,
    audit: AuditPort,
    metadata_coordinator: MetadataCoordinator | None,
    silver_validator: SilverValidatorPort | None,
) -> StorageAdapter:
    """Create StorageAdapter with Bronze/Silver/Gold writers."""
    metadata_atomic_retry_policy = create_silver_atomic_retry_policy(settings)
    merge_resilience_policy = create_silver_merge_resilience_policy(settings)
    silver_writer = create_silver_layer_writer_impl(
        ctx=ctx,
        silver_writer_cls=silver_writer_cls,
        config=config,
        logger=logger,
        metrics=metrics,
        tracing=tracing,
        metadata_coordinator=metadata_coordinator,
        silver_validator=silver_validator,
        audit=audit,
        metadata_atomic_retry_policy=metadata_atomic_retry_policy,
        merge_resilience_policy=merge_resilience_policy,
        support=_SilverLayerWriterSupport(
            resolve_delta_writer_base_path_fn=resolve_delta_writer_base_path,
            resolve_delta_writer_flat_structure_fn=resolve_delta_writer_flat_structure,
            load_contract_rollout_policy_fn=load_contract_rollout_policy,
        ),
    )
    gold_writer = create_gold_layer_writer_impl(
        ctx=ctx,
        gold_writer_cls=gold_writer_cls,
        config=config,
        logger=logger,
        metrics=metrics,
        tracing=tracing,
        metadata_coordinator=metadata_coordinator,
        audit=audit,
        resolve_delta_writer_base_path_fn=resolve_delta_writer_base_path,
        resolve_delta_writer_flat_structure_fn=resolve_delta_writer_flat_structure,
        load_contract_rollout_policy_fn=load_contract_rollout_policy,
    )
    bronze_writer = create_bronze_writer(
        writer_cls=bronze_writer_cls,
        base_path=ctx.bronze_path,
        config=ctx.bronze_config,
        logger=logger,
        metrics=metrics,
        tracing=tracing,
        metadata_coordinator=metadata_coordinator,
        audit=audit,
        flat_structure=ctx.bronze_flat,
    )
    return StorageAdapter(
        bronze_writer=bronze_writer,
        silver_writer=silver_writer,
        gold_writer=gold_writer,
    )
