"""Resolve one coherent schema/hash contract for a target classification run."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import TYPE_CHECKING

import pyarrow as pa

from bioetl.domain.config.target_classification import (
    TARGET_CLASSIFICATION_FIELDS,
    TargetClassificationConfig,
)
from bioetl.domain.contracts.gold import ChEMBLTargetGoldSchema
from bioetl.domain.contracts.gold.chembl_target_classification import (
    ChEMBLTargetGoldSchemaV31,
)
from bioetl.domain.entities.chembl_structures_foundation import Target
from bioetl.domain.entities.chembl_target_classification import TargetV31
from bioetl.domain.schemas.chembl.target import TargetSchema, TargetSchemaV31
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.pipeline_contract_policy import (
    PipelineContractPolicy,
)
from bioetl.infrastructure.schemas.silver_chembl_core import CHEMBL_TARGET_SCHEMA
from bioetl.infrastructure.schemas.silver_chembl_target_classification import (
    CHEMBL_TARGET_SCHEMA_V31,
)

if TYPE_CHECKING:
    from bioetl.domain.composite import ColumnGroupConfig, DataSchemaConfig


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


def _business_fields(fields: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys((*fields, *TARGET_CLASSIFICATION_FIELDS)))


def _extend_groups(
    groups: tuple[ColumnGroupConfig, ...],
) -> tuple[ColumnGroupConfig, ...]:
    if not any(group.name == "business" for group in groups):
        raise ValueError("enrich target profile requires the business column group")
    return tuple(
        replace(group, fields=_business_fields(group.fields))
        if group.name == "business"
        else group
        for group in groups
    )


def _extend_data_schema(schema: DataSchemaConfig | None) -> DataSchemaConfig | None:
    if schema is None:
        return None
    return replace(schema, column_groups=_extend_groups(schema.column_groups))


def _enrich_yaml_config(yaml_config: PipelineYamlConfig) -> PipelineYamlConfig:
    policy = yaml_config.content_hash_policy
    if policy is None or policy.contract.version not in {"3.0.0", "3.1.0"}:
        raise ValueError(
            "enrich target profile requires an explicit V30/V31 hash policy"
        )
    include = _business_fields(tuple(policy.include_fields))
    contract = policy.contract.model_copy(
        update={
            "version": "3.1.0",
            "migration_note": "Add nullable offline IUPHAR classification and its pinned profile identity.",
        }
    )
    resolved_policy = policy.model_copy(
        update={"contract": contract, "include_fields": list(include)}
    )
    groups = [
        group.model_copy(update={"fields": list(_business_fields(tuple(group.fields)))})
        if group.name == "business"
        else group
        for group in yaml_config.column_groups
    ]
    return yaml_config.model_copy(
        update={
            "content_hash_policy": resolved_policy,
            "content_hash": yaml_config.content_hash.model_copy(
                update={"include": list(include)}
            ),
            "column_groups": groups,
            "data_schema": _extend_data_schema(yaml_config.data_schema),
        }
    )


def _enrich_contract_policy(
    policy: PipelineContractPolicy,
    include_fields: tuple[str, ...],
    exclude_fields: tuple[str, ...],
) -> PipelineContractPolicy:
    raw = policy.model_dump()
    raw.update(
        active_version="3.1.0",
        hash_include=list(include_fields),
        hash_exclude=list(exclude_fields),
        rollout={
            "mode": "single",
            "read_order": ["3.1.0"],
            "write_versions": ["3.1.0"],
            "affects_hash": False,
        },
    )
    return PipelineContractPolicy.model_validate(raw)


def resolve_target_classification_profile(
    yaml_config: PipelineYamlConfig,
    contract_policy: PipelineContractPolicy | None = None,
) -> TargetClassificationSchemaProfile:
    """Select unchanged V30 or explicitly extended V31 without reading files."""
    if (yaml_config.provider, yaml_config.entity_type) != ("chembl", "target"):
        raise ValueError("target classification profiles require chembl_target")
    config = yaml_config.target_classification.to_domain()
    enrich = config.mode == "enrich"
    resolved = _enrich_yaml_config(yaml_config) if enrich else yaml_config
    policy = resolved.content_hash_policy
    if not enrich and policy is not None and policy.contract.version != "3.0.0":
        raise ValueError(
            "off/shadow target profiles require the legacy V30 hash policy"
        )
    resolved_contract = (
        _enrich_contract_policy(
            contract_policy,
            tuple(policy.include_fields) if policy else (),
            tuple(policy.exclude_fields) if policy else (),
        )
        if enrich and contract_policy is not None
        else contract_policy
    )
    if (
        resolved_contract is not None
        and resolved_contract.active_version != config.contract_version
    ):
        raise ValueError("target classification schema and contract versions disagree")
    return TargetClassificationSchemaProfile(
        config=config,
        contract_version=config.contract_version,
        entity_class=TargetV31 if enrich else Target,
        silver_schema=CHEMBL_TARGET_SCHEMA_V31 if enrich else CHEMBL_TARGET_SCHEMA,
        pandera_silver_schema=TargetSchemaV31 if enrich else TargetSchema,
        gold_schema=ChEMBLTargetGoldSchemaV31 if enrich else ChEMBLTargetGoldSchema,
        content_hash_include_fields=tuple(policy.include_fields) if policy else (),
        content_hash_exclude_fields=tuple(policy.exclude_fields) if policy else (),
        resolved_yaml_config=resolved,
        contract_policy=resolved_contract,
    )


__all__ = [
    "TargetClassificationSchemaProfile",
    "resolve_target_classification_profile",
]
