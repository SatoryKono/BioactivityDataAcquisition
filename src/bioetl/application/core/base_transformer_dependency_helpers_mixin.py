# pyright: reportUninitializedInstanceVariable=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportInvalidCast=false
# Host attrs/methods provided by concrete composition (PD2 W1).
"""Dependency-backed helpers shared by BaseTransformer."""

from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING, Any, Protocol, cast

from bioetl.domain.behavior import EntityIdentityGenerator
from bioetl.domain.ports import ContractPolicyProtocol
from bioetl.domain.types import ContentHash, EntityID, GoldRecord

if TYPE_CHECKING:
    from bioetl.application.core.base_transformer.types import ValueObjectWithFromRaw
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import PiiHasherPort

class _TransformerDependencyOwner(Protocol):
    """Structural contract for dependency-backed transformer helpers."""

    provider: str
    entity_type: str
    GOLD_EXCLUDE_FIELDS: frozenset[str]
    _pii_hasher: PiiHasherPort
    _contract_policy: ContractPolicyProtocol
    _identity: EntityIdentityGenerator

    @staticmethod
    def _normalize_lineage_value(field_name: str, value: object) -> object:
        """Normalize lineage/meta field values after rename."""
        ...

class _BaseTransformerDependencyHelpersMixin:
    """Helpers that delegate to injected collaborators and policy objects."""

    def hash_pii_value(self, value: str | None) -> str | None:
        """Hash a single PII value."""
        owner = cast("_TransformerDependencyOwner", self)
        hashed_value: str | None = owner._pii_hasher.hash_value(value)
        return hashed_value

    def hash_pii_list(self, values: list[str] | None) -> list[str] | None:
        """Hash a list of PII values."""
        owner = cast("_TransformerDependencyOwner", self)
        hashed_values: list[str] | None = owner._pii_hasher.hash_list(values)
        return hashed_values

    @staticmethod
    def validate_value_object(
        vo_class: type[ValueObjectWithFromRaw[Any]],  # Any: generic VO type param
        value: object,
        *,
        as_string: bool = True,
    ) -> str | int | None:
        """Validate a value using a Value Object and return normalized value."""
        vo = vo_class.from_raw(value)
        if vo is None:
            return None
        return str(vo) if as_string else vo.value

    @staticmethod
    def validate_value_objects(
        vo_class: type[ValueObjectWithFromRaw[Any]],  # Any: generic VO type param
        values: list[object] | None,
        *,
        as_string: bool = True,
    ) -> list[str | int] | None:
        """Validate a list of values using a Value Object."""
        if not values:
            return None
        result: list[str | int] = []
        for val in values:
            vo = vo_class.from_raw(val)
            if vo is not None:
                result.append(str(vo) if as_string else vo.value)
        return result if result else None

    def transform_for_gold(
        self,
        _context: PipelineContext,
        silver_record: GoldRecord,
    ) -> GoldRecord:
        """Transform Silver record for Gold layer."""
        owner = cast("_TransformerDependencyOwner", self)
        exclude_fields = owner.GOLD_EXCLUDE_FIELDS
        return {k: v for k, v in silver_record.items() if k not in exclude_fields}

    def compute_content_hash(
        self,
        business_data: GoldRecord,
        *,
        exclude_none: bool = True,
    ) -> ContentHash:
        """Generate canonical content hash for record versioning."""
        owner = cast("_TransformerDependencyOwner", self)
        hash_input = self._apply_hash_policy(
            owner._identity,
            owner._contract_policy,
            business_data,
        )
        return owner._identity.compute_content_hash(
            owner.provider,
            hash_input,
            exclude_none=exclude_none,
        )

    def compute_entity_id(
        self,
        source_id: str | None,
        record: GoldRecord,
    ) -> EntityID:
        """Generate stable entity identifier."""
        owner = cast("_TransformerDependencyOwner", self)
        return owner._identity.compute_entity_id(
            provider=owner.provider,
            entity_type=owner.entity_type,
            source_id=source_id,
            record=record,
        )

    def entity_to_silver_record(
        self,
        entity: object,
    ) -> GoldRecord:
        """Convert Domain Entity to SilverRecord format using policy rename map."""
        owner = cast("_TransformerDependencyOwner", self)
        if not dataclasses.is_dataclass(entity) or isinstance(entity, type):
            raise TypeError(f"Expected dataclass entity, got {type(entity).__name__}")

        silver_record = dataclasses.asdict(entity)
        rename_map = owner._contract_policy.rename_map
        for source_key, target_key in rename_map.items():
            if source_key in silver_record and target_key not in silver_record:
                value = silver_record.pop(source_key)
                silver_record[target_key] = owner._normalize_lineage_value(
                    source_key,
                    value,
                )

        return silver_record

    @staticmethod
    def _apply_hash_policy(
        identity_service: EntityIdentityGenerator,
        contract_policy: ContractPolicyProtocol,
        business_data: GoldRecord,
    ) -> GoldRecord:
        """Apply legacy contract hash policy only when no explicit identity policy exists."""
        identity_include = getattr(
            identity_service, "_content_hash_include_fields", None
        )
        identity_exclude = getattr(
            identity_service, "_content_hash_exclude_fields", None
        )
        if identity_include or identity_exclude:
            return dict(business_data)

        include_fields = contract_policy.hash_include
        exclude_fields = set(contract_policy.hash_exclude)

        if include_fields:
            scoped = {
                key: business_data.get(key)
                for key in include_fields
                if key in business_data
            }
        else:
            scoped = dict(business_data)

        for field in exclude_fields:
            scoped.pop(field, None)

        return scoped
