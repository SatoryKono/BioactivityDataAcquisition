"""Resolve one coherent schema/hash contract for a target classification run."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING, cast

import pyarrow as pa

from bioetl.domain.config.target_classification import (
    TARGET_CLASSIFICATION_DETAIL_FIELDS,
    TARGET_CLASSIFICATION_FIELDS,
    TargetClassificationConfig,
)
from bioetl.domain.contracts.gold.chembl_target_classification import (
    ChEMBLTargetGoldSchema,
    ChEMBLTargetGoldSchemaV31,
    ChEMBLTargetGoldSchemaV32,
    Target,
    TargetSchema,
    TargetSchemaV31,
    TargetSchemaV32,
    TargetV31,
    TargetV32,
    target_v31_schema_hash,
    target_v32_schema_hash,
)
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.pipeline_contract_policy import (
    PipelineContractPolicy,
)
from bioetl.infrastructure.schemas.silver_chembl_core import CHEMBL_TARGET_SCHEMA
from bioetl.infrastructure.schemas.silver_chembl_target_classification import (
    CHEMBL_TARGET_SCHEMA_V31,
    CHEMBL_TARGET_SCHEMA_V32,
)

if TYPE_CHECKING:
    from bioetl.domain.composite import ColumnGroupConfig, DataSchemaConfig
    from bioetl.infrastructure.schemas.pipeline_config_common_schemas import (
        AuthoritativeContentHashPolicyConfig,
    )


def _policy_fields(
    policy: AuthoritativeContentHashPolicyConfig | None,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    if policy is None:
        return (), ()
    return tuple(policy.include_fields), tuple(policy.exclude_fields)


def _contract_for_version(
    *,
    table_contract: str,
    contract_policy: PipelineContractPolicy | None,
    policy: AuthoritativeContentHashPolicyConfig | None,
) -> PipelineContractPolicy | None:
    if table_contract == "3.0.0" or contract_policy is None:
        return contract_policy
    include_fields, exclude_fields = _policy_fields(policy)
    return _enrich_contract_policy(
        contract_policy, table_contract, include_fields, exclude_fields
    )


@dataclass(frozen=True, slots=True)
class TargetClassificationSchemaProfile:
    """One selected contract, never an implicit generic dual-write mapping."""

    config: TargetClassificationConfig
    contract_version: str
    entity_class: type[Target]
    silver_schema: pa.Schema
    pandera_silver_schema: type[TargetSchema]
    gold_schema: type[ChEMBLTargetGoldSchema]
    content_hash_include_fields: tuple[str, ...]
    content_hash_exclude_fields: tuple[str, ...]
    resolved_yaml_config: PipelineYamlConfig
    contract_policy: PipelineContractPolicy | None


def _business_fields(fields: tuple[str, ...], table_contract: str) -> tuple[str, ...]:
    extra = TARGET_CLASSIFICATION_FIELDS
    if table_contract == "3.2.0":
        extra = (*extra, *TARGET_CLASSIFICATION_DETAIL_FIELDS)
    return tuple(dict.fromkeys((*fields, *extra)))


def _extend_groups(
    groups: tuple[ColumnGroupConfig, ...],
    table_contract: str,
) -> tuple[ColumnGroupConfig, ...]:
    if not any(group.name == "business" for group in groups):
        raise ValueError("enrich target profile requires the business column group")
    return tuple(
        replace(group, fields=_business_fields(group.fields, table_contract))
        if group.name == "business"
        else group
        for group in groups
    )


def _extend_data_schema(
    schema: DataSchemaConfig | None, table_contract: str
) -> DataSchemaConfig | None:
    if schema is None:
        return None
    return replace(
        schema, column_groups=_extend_groups(schema.column_groups, table_contract)
    )


def _accepted_source_versions(table_contract: str) -> frozenset[str]:
    if table_contract == "3.2.0":
        return frozenset({"3.0.0", "3.1.0", "3.2.0"})
    return frozenset({"3.0.0", "3.1.0"})


def _migration_note(table_contract: str) -> str:
    if table_contract == "3.2.0":
        return (
            "Add nullable IUPHAR classification detail: source type, completeness, "
            "family ids, subclasses, structured paths, local rules and evidence refs."
        )
    return "Add nullable offline IUPHAR classification and its pinned profile identity."


def _enrich_yaml_config(
    yaml_config: PipelineYamlConfig, table_contract: str
) -> PipelineYamlConfig:
    policy = yaml_config.content_hash_policy
    if policy is None or policy.contract.version not in _accepted_source_versions(
        table_contract
    ):
        if table_contract == "3.1.0":
            detail = "explicit V30/V31"
        else:
            detail = "explicit " + "/".join(
                sorted(_accepted_source_versions(table_contract))
            )
        raise ValueError(f"enrich target profile requires an {detail} hash policy")
    include = _business_fields(tuple(policy.include_fields), table_contract)
    contract = policy.contract.model_copy(
        update={
            "version": table_contract,
            "migration_note": _migration_note(table_contract),
        }
    )
    resolved_policy = policy.model_copy(
        update={"contract": contract, "include_fields": list(include)}
    )
    groups = [
        group.model_copy(
            update={
                "fields": list(_business_fields(tuple(group.fields), table_contract))
            }
        )
        if group.name == "business"
        else group
        for group in yaml_config.column_groups
    ]
    return yaml_config.model_copy(
        update={
            "content_hash_policy": resolved_policy,
            "content_hash": yaml_config.content_hash.model_copy(
                update={
                    "include": list(include),
                    "exclude": list(policy.exclude_fields),
                }
            ),
            "column_groups": groups,
            "data_schema": _extend_data_schema(yaml_config.data_schema, table_contract),
        }
    )


def _enrich_contract_policy(
    policy: PipelineContractPolicy,
    table_contract: str,
    include_fields: tuple[str, ...],
    exclude_fields: tuple[str, ...],
) -> PipelineContractPolicy:
    raw = policy.model_dump()
    raw.update(
        active_version=table_contract,
        hash_include=list(include_fields),
        hash_exclude=list(exclude_fields),
        rollout={
            "mode": "single",
            "read_order": [table_contract],
            "write_versions": [table_contract],
            "affects_hash": False,
        },
    )
    return PipelineContractPolicy.model_validate(raw)


def _target_schemas(
    table_contract: str,
) -> tuple[type[Target], pa.Schema, type[TargetSchema], type[ChEMBLTargetGoldSchema]]:
    """Select all four schema representations as one coherent physical version."""
    if table_contract == "3.2.0":
        return (
            TargetV32,
            CHEMBL_TARGET_SCHEMA_V32,
            cast(type[TargetSchema], TargetSchemaV32),
            cast(type[ChEMBLTargetGoldSchema], ChEMBLTargetGoldSchemaV32),
        )
    if table_contract == "3.1.0":
        return (
            TargetV31,
            CHEMBL_TARGET_SCHEMA_V31,
            TargetSchemaV31,
            ChEMBLTargetGoldSchemaV31,
        )
    return Target, CHEMBL_TARGET_SCHEMA, TargetSchema, ChEMBLTargetGoldSchema


def resolve_target_classification_profile(
    yaml_config: PipelineYamlConfig,
    contract_policy: PipelineContractPolicy | None = None,
) -> TargetClassificationSchemaProfile:
    """Select V30, V31 or explicit V32 without reading files."""
    if (yaml_config.provider, yaml_config.entity_type) != ("chembl", "target"):
        raise ValueError("target classification profiles require chembl_target")
    config = yaml_config.target_classification.to_domain()
    table_contract = config.contract_version
    resolved = (
        _enrich_yaml_config(yaml_config, table_contract)
        if table_contract != "3.0.0"
        else yaml_config
    )
    policy = resolved.content_hash_policy
    if (
        table_contract == "3.0.0"
        and policy is not None
        and policy.contract.version != "3.0.0"
    ):
        raise ValueError(
            "off/shadow target profiles require the legacy V30 hash policy"
        )
    resolved_contract = _contract_for_version(
        table_contract=table_contract,
        contract_policy=contract_policy,
        policy=policy,
    )
    if (
        resolved_contract is not None
        and resolved_contract.active_version != config.contract_version
    ):
        raise ValueError("target classification schema and contract versions disagree")
    include_fields, exclude_fields = _policy_fields(policy)
    entity_class, silver_schema, pandera_schema, gold_schema = _target_schemas(
        table_contract
    )
    return TargetClassificationSchemaProfile(
        config=config,
        contract_version=config.contract_version,
        entity_class=entity_class,
        silver_schema=silver_schema,
        pandera_silver_schema=pandera_schema,
        gold_schema=gold_schema,
        content_hash_include_fields=include_fields,
        content_hash_exclude_fields=exclude_fields,
        resolved_yaml_config=resolved,
        contract_policy=resolved_contract,
    )


__all__ = [
    "ChEMBLTargetGoldSchemaV31",
    "ChEMBLTargetGoldSchemaV32",
    "TargetClassificationSchemaProfile",
    "resolve_target_classification_profile",
    "target_v31_schema_hash",
    "target_v32_schema_hash",
]
