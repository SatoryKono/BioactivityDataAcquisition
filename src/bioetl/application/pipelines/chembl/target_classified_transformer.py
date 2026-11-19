"""Schema 3.1 target transformer selected only by the enrich profile."""

from __future__ import annotations

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.domain.entities.chembl_target_classification import TargetV31
from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v31_normalization_profile,
)
from bioetl.domain.types import ContentHash, JsonDict


class TargetClassifiedTransformer(TargetTransformer):
    """Keep the legacy target entity and optional-classified entity separate."""

    entity_class = TargetV31

    def _build_record_normalizer(self) -> RecordNormalizationProcessor:
        return RecordNormalizationProcessor(
            provider=self.provider,
            entity_type=self.entity_type,
            profile=target_v31_normalization_profile(),
            content_hash_policy_authoritative=True,
            content_hash_include_fields=frozenset(self._contract_policy.hash_include),
            content_hash_exclude_fields=frozenset(self._contract_policy.hash_exclude),
        )

    def compute_content_hash(
        self, business_data: JsonDict, *, exclude_none: bool = True
    ) -> ContentHash:
        """Use the same canonical V31 hash semantics as staged normalization."""
        del exclude_none
        return ContentHash(
            self._get_record_normalizer().compute_content_hash(business_data)
        )


__all__ = ["TargetClassifiedTransformer"]
