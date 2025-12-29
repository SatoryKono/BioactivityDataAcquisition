"""ChEMBL Target Relation Transformer.

Transforms Bronze records to Silver format (TargetRelation entity inflation).
Handles composite key: (target_chembl_id, related_target_chembl_id, relationship).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import TargetRelation
from bioetl.domain.types import EntityID

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class TargetRelationTransformer(BaseTransformer):
    """Transforms ChEMBL bronze target relation records to silver.

    Target relations form a directed graph describing relationships between
    biological targets (subtypes, variants, complexes).

    Uses composite key for entity_id: (target_chembl_id, related_target_chembl_id, relationship).
    """

    def __init__(
        self,
        provider: str = "chembl",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
    ) -> None:
        """Initialize ChEMBL Target Relation transformer.

        Args:
            provider: Data provider identifier. Defaults to 'chembl'.
            tracer: Optional tracing port for distributed tracing (O1 observability).
            metrics: Optional metrics port for duration/error tracking (O1 observability).
            gold_filters: Optional filter configuration for Gold layer.

        """
        super().__init__(
            provider, tracer=tracer, metrics=metrics, gold_filters=gold_filters
        )

    def _normalize_relationship(self, value: Any) -> str:
        """Normalize relationship type by stripping and uppercasing.

        Args:
            value: Raw relationship value from API.

        Returns:
            Normalized relationship string (stripped and uppercased).

        Raises:
            ValueError: If relationship is None or empty after normalization.

        """
        if value is None:
            raise ValueError("Relationship is required")
        normalized = str(value).strip().upper()
        if not normalized:
            raise ValueError("Relationship cannot be empty")
        return normalized

    def _normalize_chembl_id(self, value: Any, field_name: str) -> str:
        """Normalize ChEMBL ID by stripping whitespace.

        Args:
            value: Raw ChEMBL ID value from API.
            field_name: Field name for error message.

        Returns:
            Normalized ChEMBL ID string.

        Raises:
            ValueError: If ChEMBL ID is None or empty.

        """
        if value is None:
            raise ValueError(f"{field_name} is required")
        normalized = str(value).strip()
        if not normalized:
            raise ValueError(f"{field_name} cannot be empty")
        return normalized

    def _generate_composite_entity_id(
        self,
        target_chembl_id: str,
        related_target_chembl_id: str,
        relationship: str,
    ) -> EntityID:
        """Generate entity ID from composite key.

        Format: chembl:{target_chembl_id}_{related_target_chembl_id}_{relationship}

        Args:
            target_chembl_id: The child target ChEMBL ID.
            related_target_chembl_id: The related target ChEMBL ID.
            relationship: The relationship type (normalized, uppercase).

        Returns:
            EntityID with composite key format.

        """
        # Replace spaces in relationship with underscores for cleaner ID
        relationship_key = relationship.replace(" ", "_")
        stable_id = f"{target_chembl_id}_{related_target_chembl_id}_{relationship_key}"
        return EntityID(f"{self.provider}:{stable_id}")

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform a single target relation record.

        Overrides base implementation to handle composite key entity_id generation.

        Steps:
        1. Extract and normalize composite key fields
        2. Generate entity_id from composite key
        3. Compute content hash
        4. Create domain entity with validation
        5. Convert to SilverRecord

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from ChEMBL API.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        """
        # 1. Extract and normalize composite key fields
        target_chembl_id = self._normalize_chembl_id(
            record.get("target_chembl_id"), "target_chembl_id"
        )
        related_target_chembl_id = self._normalize_chembl_id(
            record.get("related_target_chembl_id"), "related_target_chembl_id"
        )
        relationship = self._normalize_relationship(record.get("relationship"))

        # 2. Generate entity_id from composite key
        entity_id = self._generate_composite_entity_id(
            target_chembl_id, related_target_chembl_id, relationship
        )

        # 3. Build business data
        business_data = {
            "target_chembl_id": target_chembl_id,
            "related_target_chembl_id": related_target_chembl_id,
            "relationship": relationship,
        }

        # 4. Compute content hash
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # 5. Create domain entity with validation
        entity = self._create_entity(
            TargetRelation,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # 6. Convert to SilverRecord
        return cast("SilverRecord", self.entity_to_silver_record(entity))
