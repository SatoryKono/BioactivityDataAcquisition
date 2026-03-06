"""Base Transformer class for Bronze -> Silver transformations."""

from __future__ import annotations

import dataclasses
import time
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, cast

from bioetl.application.core.base_transformer.contract_policy import (
    _DefaultContractPolicy,
)
from bioetl.application.core.base_transformer.errors import (
    FilteredOutError,
    TransformationError,
)
from bioetl.application.core.base_transformer.types import T, ValueObjectWithFromRaw
from bioetl.application.core.base_transformer_helpers_mixin import (
    _BaseTransformerRecordHelpersMixin,
)
from bioetl.domain.ports import (
    ContractPolicyPort,
    DataNormalizationPort,
    MetricsPort,
    NoOpMetrics,
    NoOpPiiHasher,
    NoOpTracing,
    PiiHasherPort,
    TracingPort,
)
from bioetl.domain.services import DataNormalizationService, IdentityService
from bioetl.domain.types import ContentHash, EntityID, GoldRecord

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig, SilverFilterConfig
    from bioetl.domain.types import BronzeRecord, SilverRecord

__all__ = ["BaseTransformer", "T"]


def _apply_hash_policy(
    contract_policy: ContractPolicyPort,
    business_data: GoldRecord,
) -> GoldRecord:
    """Apply include/exclude hash policy from contract config."""
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


class BaseTransformer(_BaseTransformerRecordHelpersMixin, ABC):
    """Abstract base class for Bronze -> Silver transformers."""

    GOLD_EXCLUDE_FIELDS: ClassVar[frozenset[str]] = frozenset()

    def __init__(
        self,
        provider: str,
        entity_type: str | None = None,
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        silver_filters: SilverFilterConfig | None = None,
        gold_filters: GoldFilterConfig | None = None,
        identity_service: IdentityService | None = None,
        pii_hasher: PiiHasherPort | None = None,
        data_normalizer: DataNormalizationPort | None = None,
        contract_policy: ContractPolicyPort | None = None,
    ) -> None:
        """Initialize transformer with provider context and overridable services."""
        self.provider = provider
        self.entity_type = entity_type or "unknown"
        self._tracer: TracingPort = tracer if tracer is not None else NoOpTracing()
        self._metrics: MetricsPort = metrics if metrics is not None else NoOpMetrics()
        self._silver_filters = silver_filters
        self._gold_filters = gold_filters
        self._identity: IdentityService = (
            identity_service if identity_service is not None else IdentityService()
        )
        self._pii_hasher: PiiHasherPort = (
            pii_hasher if pii_hasher is not None else NoOpPiiHasher()
        )
        self._data_normalizer: DataNormalizationPort = (
            data_normalizer
            if data_normalizer is not None
            else DataNormalizationService()
        )
        resolved_contract_policy: ContractPolicyPort = (
            contract_policy if contract_policy is not None else _DefaultContractPolicy()
        )
        self._contract_policy = resolved_contract_policy

    def hash_pii_value(self, value: str | None) -> str | None:
        """Hash a single PII value."""
        return self._pii_hasher.hash_value(value)

    def hash_pii_list(self, values: list[str] | None) -> list[str] | None:
        """Hash a list of PII values."""
        return self._pii_hasher.hash_list(values)

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

    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform Bronze record to Silver format (Template Method)."""
        start_time = time.perf_counter()
        error_type: str | None = None

        otel_tracer = self._tracer.get_tracer("bioetl.transformer")
        span = otel_tracer.start_as_current_span(
            "transform_record",
            attributes={
                "bioetl.provider": self.provider,
                "bioetl.entity_type": self.entity_type,
                "bioetl.run_id": str(context.run_id),
                "bioetl.record_index": index,
            },
        )
        span.__enter__()

        try:
            result = await self._transform_impl(context, record, index)
            if result is not None and not self.should_write_silver(
                context,
                cast("GoldRecord", result),
            ):
                context.logger.debug(
                    "silver_filter_excluded",
                    provider=self.provider,
                    entity_type=self.entity_type,
                    record_index=index,
                )
                raise FilteredOutError()
            return result
        except TransformationError as e:
            error_type = "transformation_error"
            context.logger.warning(
                "transformation_skipped",
                reason=str(e),
                field=e.field,
                provider=self.provider,
            )
            span.set_attribute("error", True)
            span.set_attribute("error.type", error_type)
            return None
        except ValueError as e:
            error_type = "validation_error"
            context.logger.warning(
                "entity_validation_failed",
                error=str(e),
                provider=self.provider,
            )
            span.set_attribute("error", True)
            span.set_attribute("error.type", error_type)
            return None
        finally:
            duration = time.perf_counter() - start_time
            self._metrics.observe_histogram(
                "transform_duration_seconds",
                duration,
                labels={
                    "provider": self.provider,
                    "entity_type": self.entity_type,
                },
            )
            if error_type:
                self._metrics.increment_counter(
                    "transform_errors_total",
                    1,
                    labels={
                        "provider": self.provider,
                        "entity_type": self.entity_type,
                        "error_type": error_type,
                    },
                )
            span.set_attribute("bioetl.duration_ms", duration * 1000)
            span.__exit__(None, None, None)

    @abstractmethod
    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Implement entity-specific transformation logic."""
        ...

    def should_write_silver(
        self,
        _context: PipelineContext,
        record: GoldRecord,
    ) -> bool:
        """Determine whether transformed record should be written to Silver."""
        if self._silver_filters is None or self._silver_filters.is_empty():
            return True
        return self._silver_filters.should_include(record)

    def should_write_gold(
        self,
        _context: PipelineContext,
        record: GoldRecord,
    ) -> bool:
        """Determine whether transformed record should be written to Gold."""
        if self._gold_filters is None or self._gold_filters.is_empty():
            return True
        return self._gold_filters.should_include(record)

    def transform_for_gold(
        self,
        _context: PipelineContext,
        silver_record: GoldRecord,
    ) -> GoldRecord:
        """Transform Silver record for Gold layer."""
        return {
            k: v for k, v in silver_record.items() if k not in self.GOLD_EXCLUDE_FIELDS
        }

    def compute_content_hash(
        self,
        business_data: GoldRecord,
        *,
        exclude_none: bool = True,
    ) -> ContentHash:
        """Generate canonical content hash for record versioning."""
        hash_input = _apply_hash_policy(self._contract_policy, business_data)
        return self._identity.compute_content_hash(
            self.provider,
            hash_input,
            exclude_none=exclude_none,
        )

    def compute_entity_id(
        self,
        source_id: str | None,
        record: GoldRecord,
    ) -> EntityID:
        """Generate stable entity identifier."""
        return self._identity.compute_entity_id(
            provider=self.provider,
            entity_type=self.entity_type,
            source_id=source_id,
            record=record,
        )

    def entity_to_silver_record(
        self,
        entity: object,
    ) -> GoldRecord:
        """Convert Domain Entity to SilverRecord format using policy rename map."""
        if not dataclasses.is_dataclass(entity) or isinstance(entity, type):
            raise TypeError(f"Expected dataclass entity, got {type(entity).__name__}")

        silver_record = dataclasses.asdict(entity)
        rename_map = self._contract_policy.rename_map
        for source_key, target_key in rename_map.items():
            if source_key in silver_record and target_key not in silver_record:
                value = silver_record.pop(source_key)
                silver_record[target_key] = self._normalize_lineage_value(
                    source_key,
                    value,
                )

        return silver_record
