"""Schema 3.1 and 3.2 target transformers selected only by the enrich profile.

Default contract 3.1.0; explicit 3.2.0 is opt-in.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
from bioetl.domain.entities.chembl_target_classification import TargetV31, TargetV32
from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v31_normalization_profile,
    target_v32_normalization_profile,
)
from bioetl.domain.types import ContentHash, GoldRecord, JsonDict


class TargetClassifiedTransformer(TargetTransformer):
    """Keep the legacy target entity and optional-classified entity separate."""

    entity_class = TargetV31

    def _classification_contract(self) -> str:
        version = getattr(self._contract_policy, "active_version", None)
        if version == "3.2.0":
            return "3.2.0"
        return "3.1.0"

    def _build_record_normalizer(self) -> RecordNormalizationProcessor:
        profile = (
            target_v32_normalization_profile()
            if self._classification_contract() == "3.2.0"
            else target_v31_normalization_profile()
        )
        return RecordNormalizationProcessor(
            provider=self.provider,
            entity_type=self.entity_type,
            profile=profile,
            content_hash_policy_authoritative=True,
            content_hash_include_fields=frozenset(self._contract_policy.hash_include),
            content_hash_exclude_fields=frozenset(self._contract_policy.hash_exclude),
        )

    def _build_pre_silver_record(
        self,
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        index: int,
        business_data: JsonDict,
    ) -> GoldRecord:
        entity_class = (
            TargetV32
            if self._classification_contract() == "3.2.0"
            else self.entity_class
        )
        entity = self._create_entity(
            entity_class,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )
        silver_record = self.entity_to_silver_record(entity)
        return self._postprocess_pre_silver_record(
            silver_record,
            business_data=business_data,
        )

    def compute_content_hash(
        self, business_data: JsonDict, *, exclude_none: bool = True
    ) -> ContentHash:
        """Use the same canonical V31 hash semantics as staged normalization."""
        del exclude_none
        return ContentHash(
            self._get_record_normalizer().compute_content_hash(business_data)
        )

    @classmethod
    def for_physical_contract(
        cls, contract_version: str
    ) -> type[TargetClassifiedTransformer]:
        """Return the enrich transformer for one physical contract."""
        if contract_version == "3.2.0":
            return TargetClassifiedDetailTransformer
        return cls


class TargetClassifiedDetailTransformer(TargetClassifiedTransformer):
    """Select the 3.2.0 entity and canonical detail normalization."""

    entity_class = TargetV32

    def _build_record_normalizer(self) -> RecordNormalizationProcessor:
        return RecordNormalizationProcessor(
            provider=self.provider,
            entity_type=self.entity_type,
            profile=target_v32_normalization_profile(),
            content_hash_policy_authoritative=True,
            content_hash_include_fields=frozenset(self._contract_policy.hash_include),
            content_hash_exclude_fields=frozenset(self._contract_policy.hash_exclude),
        )


__all__ = ["TargetClassifiedDetailTransformer", "TargetClassifiedTransformer"]
