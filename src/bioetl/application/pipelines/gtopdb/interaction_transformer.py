"""GtoPdb Interaction Transformer.

Transforms raw GtoPdb interaction records into Silver-layer format using
the GtopdbInteraction domain entity for validation and invariant checking.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import GtopdbInteraction
from bioetl.domain.transformations import generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.filtering import GoldFilterConfig
    from bioetl.domain.ports import MetricsPort, TracingPort
    from bioetl.domain.types import BronzeRecord, SilverRecord


class GtopdbInteractionTransformer(BaseTransformer):
    """Transformer for GtoPdb interaction records.

    Uses GtopdbInteraction domain entity for validation and lineage tracking.

    GtoPdb API field mapping:
    - interactionId -> interaction_id
    - targetId -> target_id
    - ligandId -> ligand_id
    - type -> interaction_type
    - action -> action
    - affinityParameter -> affinity_type
    - affinityValue -> affinity_value
    - pubmedIds -> pubmed_ids (JSON list)
    """

    def __init__(
        self,
        provider: str = "gtopdb",
        tracer: TracingPort | None = None,
        metrics: MetricsPort | None = None,
        gold_filters: GoldFilterConfig | None = None,
    ):
        """Initialize GtoPdb interaction transformer.

        Args:
            provider: Data provider identifier.
            tracer: Optional tracing port for distributed tracing.
            metrics: Optional metrics port for duration/error tracking.
            gold_filters: Optional filter configuration for Gold layer.
        """
        super().__init__(
            provider,
            entity_type="interaction",
            tracer=tracer,
            metrics=metrics,
            gold_filters=gold_filters,
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Transform raw GtoPdb interaction record to Silver format.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Raw Bronze record from GtoPdb.
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        Raises:
            TransformationError: If required fields are missing.
            ValueError: If GtopdbInteraction entity validation fails.
        """
        # Step 1: Validate required fields
        interaction_id = self._get_required_field(record, "interactionId")
        target_id = self._get_required_field(record, "targetId")
        ligand_id = self._get_required_field(record, "ligandId")

        # Step 2: Build business data dictionary with field mapping
        business_data: dict[str, Any] = {
            "interaction_id": int(interaction_id),
            "target_id": int(target_id),
            "ligand_id": int(ligand_id),
            # Interaction type
            "interaction_type": record.get("type"),
            "action": record.get("action"),
            "action_comment": record.get("actionComment"),
            "selectivity": record.get("selectivity"),
            # Affinity data
            "affinity_type": record.get("affinityParameter"),
            "affinity_value": self._safe_float(record.get("affinityValue")),
            "affinity_low": self._safe_float(record.get("affinityLow")),
            "affinity_high": self._safe_float(record.get("affinityHigh")),
            "affinity_median": self._safe_float(record.get("affinityMedian")),
            "affinity_units": record.get("affinityUnits"),
            "affinity_qualifier": record.get("affinityQualifier"),
            # Species context
            "species": record.get("species"),
            "species_id": self._safe_int(record.get("speciesId")),
            # Flags
            "endogenous": self._safe_bool(record.get("endogenous")),
            "primary_target": self._safe_bool(record.get("primaryTarget")),
            # References
            "pubmed_ids": self.serialize_json(record.get("pubmedIds")),
        }

        # Step 3: Generate entity_id
        entity_id = generate_entity_id(
            record={"interactionId": interaction_id},
            provider=self.provider,
            id_field="interactionId",
        )

        # Step 4: Compute content_hash
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # Step 5: Create domain entity with lineage metadata
        entity = self._create_entity(
            GtopdbInteraction,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # Step 6: Convert to SilverRecord with lineage field renaming
        return cast("SilverRecord", self.entity_to_silver_record(entity))

    @staticmethod
    def _safe_int(value: Any) -> int | None:
        """Safely convert value to int, returning None if invalid."""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_float(value: Any) -> float | None:
        """Safely convert value to float, returning None if invalid."""
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_bool(value: Any) -> bool | None:
        """Safely convert value to bool, returning None if invalid."""
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "yes", "1")
        return bool(value)
