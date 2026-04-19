from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from bioetl.infrastructure.config.contract_policy_loader import (
    load_pipeline_contract_policy,
)

from ._gold import create_gold_writer
from ._silver import CreateSilverWriterRequest, create_silver_writer

if TYPE_CHECKING:
    from collections.abc import Callable

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
    from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
    from bioetl.infrastructure.storage.delta.resilience import (
        AdaptiveRetryPolicy,
        SilverMergeResiliencePolicy,
    )
    from bioetl.infrastructure.storage.gold_writer import GoldWriter
    from bioetl.infrastructure.storage.silver_writer import SilverWriter

    from ._context_resolution import StorageCreationContext


def load_contract_rollout_policy(config: PipelineYamlConfig) -> ContractRolloutPolicy:
    return load_pipeline_contract_policy(
        config.provider,
        config.entity_type,
    ).to_contract_rollout_policy()


@dataclass(frozen=True, slots=True)
class _SilverLayerWriterSupport:
    resolve_delta_writer_base_path_fn: Callable[..., object]
    resolve_delta_writer_flat_structure_fn: Callable[..., bool]
    load_contract_rollout_policy_fn: Callable[
        [PipelineYamlConfig], ContractRolloutPolicy
    ]


def create_silver_layer_writer_impl(
    *,
    ctx: StorageCreationContext,
    silver_writer_cls: type[SilverWriter],
    config: PipelineYamlConfig,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracing: TracingPort,
    metadata_coordinator: MetadataCoordinator | None,
    silver_validator: SilverValidatorPort | None,
    audit: AuditPort,
    metadata_atomic_retry_policy: AdaptiveRetryPolicy,
    merge_resilience_policy: SilverMergeResiliencePolicy,
    support: _SilverLayerWriterSupport,
) -> SilverWriter:
    silver_writer_flat = support.resolve_delta_writer_flat_structure_fn(
        ctx.silver_path,
        provider=config.provider,
        entity_type=config.entity_type,
        flat_structure=ctx.silver_flat,
    )
    return create_silver_writer(
        CreateSilverWriterRequest(
            writer_cls=silver_writer_cls,
            base_path=support.resolve_delta_writer_base_path_fn(
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
            audit=audit,
            transform_version=config.transform.version,
            transform_steps=tuple(config.transform.steps),
            flat_structure=silver_writer_flat,
            silver_validator=silver_validator,
            metrics=metrics,
            metadata_atomic_retry_policy=metadata_atomic_retry_policy,
            merge_resilience_policy=merge_resilience_policy,
            contract_rollout_policy=support.load_contract_rollout_policy_fn(config),
            pipeline_name=ctx.pipeline_name,
        )
    )


def create_gold_layer_writer_impl(
    *,
    ctx: StorageCreationContext,
    gold_writer_cls: type[GoldWriter],
    config: PipelineYamlConfig,
    logger: LoggerPort,
    metrics: MetricsPort,
    tracing: TracingPort,
    metadata_coordinator: MetadataCoordinator | None,
    audit: AuditPort,
    resolve_delta_writer_base_path_fn: Callable[..., object],
    resolve_delta_writer_flat_structure_fn: Callable[..., bool],
    load_contract_rollout_policy_fn: Callable[
        [PipelineYamlConfig], ContractRolloutPolicy
    ],
) -> GoldWriter:
    gold_writer_flat = resolve_delta_writer_flat_structure_fn(
        ctx.gold_path,
        provider=config.provider,
        entity_type=config.entity_type,
        flat_structure=ctx.gold_flat,
    )
    return create_gold_writer(
        writer_cls=gold_writer_cls,
        base_path=resolve_delta_writer_base_path_fn(
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
        audit=audit,
        transform_version=config.transform.version,
        transform_steps=tuple(config.transform.steps),
        flat_structure=gold_writer_flat,
        metrics=metrics,
        contract_rollout_policy=load_contract_rollout_policy_fn(config),
    )
