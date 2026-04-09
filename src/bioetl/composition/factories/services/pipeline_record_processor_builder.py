"""Record-processor assembly helpers for pipeline_builder facade."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Mapping
from itertools import chain
from typing import TYPE_CHECKING, cast

from bioetl.application.core.runtime_wiring_api import (
    BasePipeline,
    ContentHashPolicyByVersion,
    ContentHashVersionPolicy,
    RecordProcessor,
    RecordProcessorConfig,
)
from bioetl.domain.types import (
    GoldSchemaPolicyByVersion,
    GoldSchemaVersionPolicy,
)
from bioetl.infrastructure.validation import PanderaGoldValidator

if TYPE_CHECKING:
    import pandera as pdr
    import pyarrow as pa

    from bioetl.composition.bootstrap_contexts import PipelineCallbacksContext
    from bioetl.domain.config import DQConfig
    from bioetl.domain.ports import GoldValidatorPort, TracingPort
    from bioetl.domain.types import GoldSchemaType


def _coerce_string_frozenset(value: object | None) -> frozenset[str]:
    """Coerce list/set-like string collections to an immutable set."""
    if value is None or isinstance(value, str | bytes):
        return frozenset()
    if not isinstance(value, Iterable):
        return frozenset()
    return frozenset(item for item in value if isinstance(item, str))


def _extract_hash_policy(
    pipeline: BasePipeline,
) -> tuple[frozenset[str], frozenset[str]]:
    """Extract effective content-hash field policy from transformer wiring."""
    transformer = getattr(pipeline, "transformer", None)
    identity = getattr(transformer, "_identity", None)
    contract_policy = getattr(transformer, "_contract_policy", None)

    identity_include = _coerce_string_frozenset(
        getattr(identity, "_content_hash_include_fields", None)
    )
    identity_exclude = _coerce_string_frozenset(
        getattr(identity, "_content_hash_exclude_fields", None)
    )
    contract_include = _coerce_string_frozenset(
        getattr(contract_policy, "hash_include", None)
    )
    contract_exclude = _coerce_string_frozenset(
        getattr(contract_policy, "hash_exclude", None)
    )

    include_fields = (
        frozenset(contract_include & identity_include)
        if contract_include and identity_include
        else (contract_include or identity_include)
    )
    exclude_fields = frozenset(
        chain(identity_exclude, contract_exclude, ("entity_id", "content_hash"))
    )
    return include_fields, exclude_fields


def _extract_hash_policy_by_version(
    pipeline: BasePipeline,
    *,
    include_fields: frozenset[str],
    exclude_fields: frozenset[str],
) -> ContentHashPolicyByVersion | None:
    """Build ordered per-version hash policies from rollout-aware contract policy."""
    transformer = getattr(pipeline, "transformer", None)
    contract_policy = getattr(transformer, "_contract_policy", None)
    active_version = getattr(contract_policy, "active_version", None)
    rollout = getattr(contract_policy, "rollout", None)
    write_versions = getattr(rollout, "write_versions", None)
    affects_hash = bool(getattr(rollout, "affects_hash", False))

    normalized_active_version = (
        str(active_version).strip() if active_version is not None else ""
    )
    if not normalized_active_version:
        return None

    if write_versions is None:
        versions: tuple[str, ...] = (normalized_active_version,)
    else:
        versions = tuple(
            str(version).strip() for version in write_versions if str(version).strip()
        ) or (normalized_active_version,)

    if normalized_active_version not in versions:
        versions = (normalized_active_version, *versions)

    return ContentHashPolicyByVersion(
        active_version=normalized_active_version,
        affects_hash=affects_hash,
        policies=tuple(
            ContentHashVersionPolicy(
                version=version,
                include_fields=include_fields,
                exclude_fields=exclude_fields,
            )
            for version in versions
        ),
    )


def _extract_gold_schema_policy_by_version(
    pipeline: BasePipeline,
    *,
    gold_schema: GoldSchemaType,
) -> GoldSchemaPolicyByVersion | None:
    """Build ordered per-version Gold schema routing from rollout-aware policy."""
    transformer = getattr(pipeline, "transformer", None)
    contract_policy = getattr(transformer, "_contract_policy", None)
    active_version = getattr(contract_policy, "active_version", None)
    rollout = getattr(contract_policy, "rollout", None)
    write_versions = getattr(rollout, "write_versions", None)
    configured_mapping = getattr(pipeline, "gold_schema_by_version", None)

    normalized_active_version = (
        str(active_version).strip() if active_version is not None else ""
    )
    if not normalized_active_version:
        return None

    if write_versions is None:
        versions: tuple[str, ...] = (normalized_active_version,)
    else:
        versions = tuple(
            str(version).strip() for version in write_versions if str(version).strip()
        ) or (normalized_active_version,)

    if normalized_active_version not in versions:
        versions = (normalized_active_version, *versions)

    schema_mapping: dict[str, object] = {}
    if isinstance(configured_mapping, Mapping):
        schema_mapping = {
            str(version).strip(): schema
            for version, schema in configured_mapping.items()
            if str(version).strip() and schema is not None
        }

    for version in versions:
        schema_mapping.setdefault(version, gold_schema)

    return GoldSchemaPolicyByVersion(
        active_version=normalized_active_version,
        policies=tuple(
            GoldSchemaVersionPolicy(
                version=version,
                schema=schema_mapping[version],
            )
            for version in versions
        ),
    )


def build_record_processor_config_and_validator(
    *,
    pipeline: BasePipeline,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    strict_gold_validation: bool,
    bronze_output_path: str | None,
    silver_output_path: str | None,
    gold_output_path: str | None,
    flat_structure: bool,
    gold_validator_factory: Callable[..., GoldValidatorPort] = PanderaGoldValidator,
) -> tuple[RecordProcessorConfig, GoldValidatorPort]:
    """Build RecordProcessorConfig plus Gold validator from pipeline state."""
    include_fields, exclude_fields = _extract_hash_policy(pipeline)
    hash_policy_by_version = _extract_hash_policy_by_version(
        pipeline,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
    )
    gold_schema_policy_by_version = _extract_gold_schema_policy_by_version(
        pipeline,
        gold_schema=gold_schema,
    )
    active_gold_schema = (
        gold_schema_policy_by_version.active_schema
        if gold_schema_policy_by_version is not None
        else gold_schema
    )
    processor_config = RecordProcessorConfig(
        pipeline_name=pipeline.config.pipeline_name,
        provider=pipeline.config.provider,
        entity_type=pipeline.config.entity_type,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        dq_config=cast("DQConfig | None", pipeline.config.dq),
        table_config=pipeline.config.table,
        bronze_output_path=bronze_output_path,
        silver_output_path=silver_output_path,
        gold_output_path=gold_output_path,
        flat_structure=flat_structure,
        column_groups=pipeline.config.column_groups,
        scd_config=pipeline.config.scd_config,
        content_hash_include_fields=include_fields,
        content_hash_exclude_fields=exclude_fields,
        content_hash_policy_by_version=hash_policy_by_version,
        gold_schema_policy_by_version=gold_schema_policy_by_version,
    )
    gold_validator = gold_validator_factory(
        cast("pdr.DataFrameSchema | None", active_gold_schema),
        strict=strict_gold_validation,
    )
    return processor_config, gold_validator


def create_record_processor_from_pipeline(
    *,
    pipeline: BasePipeline,
    silver_schema: pa.Schema | None,
    gold_schema: GoldSchemaType,
    callbacks: PipelineCallbacksContext,
    create_record_processor_fn: Callable[..., RecordProcessor],
    strict_gold_validation: bool = True,
    lock_validator: Callable[[], Awaitable[bool]] | None = None,
    tracer: TracingPort | None = None,
) -> RecordProcessor:
    """Project pipeline fields into the injected record-processor factory."""
    include_fields, exclude_fields = _extract_hash_policy(pipeline)
    hash_policy_by_version = _extract_hash_policy_by_version(
        pipeline,
        include_fields=include_fields,
        exclude_fields=exclude_fields,
    )
    gold_schema_policy_by_version = _extract_gold_schema_policy_by_version(
        pipeline,
        gold_schema=gold_schema,
    )
    return create_record_processor_fn(
        services=pipeline.services,
        context=pipeline.context,
        pipeline_name=pipeline.config.pipeline_name,
        provider=pipeline.config.provider,
        entity_type=pipeline.config.entity_type,
        silver_schema=silver_schema,
        gold_schema=gold_schema,
        dq_config=pipeline.config.dq,
        primary_keys=pipeline.config.table.primary_keys,
        silver_table=pipeline.config.effective_silver_table,
        gold_table=pipeline.config.effective_gold_table,
        silver_write_mode=pipeline.config.table.silver_write_mode,
        gold_write_mode=pipeline.config.table.gold_write_mode,
        on_schema_mismatch=pipeline.config.table.on_schema_mismatch,
        transform_callback=callbacks.transform,
        gold_filter_callback=callbacks.gold_filter,
        gold_transform_callback=callbacks.gold_transform,
        strict_gold_validation=strict_gold_validation,
        lock_validator=lock_validator,
        tracer=tracer,
        column_groups=tuple(pipeline.config.column_groups),
        scd_config=pipeline.config.scd_config,
        content_hash_include_fields=include_fields,
        content_hash_exclude_fields=exclude_fields,
        content_hash_policy_by_version=hash_policy_by_version,
        gold_schema_policy_by_version=gold_schema_policy_by_version,
    )
