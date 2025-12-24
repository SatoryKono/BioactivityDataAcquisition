"""ChEMBL Target Component Transformer.

Transforms Bronze records to Silver format (Target Component entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import TargetComponent
from bioetl.domain.transformations import generate_entity_id, safe_int

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


class TargetComponentTransformer(BaseTransformer):
    """Transforms ChEMBL bronze target component records to silver."""

    def __init__(self, provider: str = "chembl"):
        """Initialize ChEMBL target component transformer.

        Args:
            provider: Data provider identifier.

        """
        super().__init__(provider)

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL target component to normalized format using Domain Entity."""
        # Validate required field
        component_id = self._get_required_field(record, "component_id")

        entity_id = generate_entity_id(
            record={"component_id": str(component_id)},
            provider=self.provider,
            id_field="component_id",
        )

        business_data: dict[str, Any] = {
            # Primary identifier
            "component_id": safe_int(component_id),
            # Core metadata
            "accession": record.get("accession"),
            "component_type": record.get("component_type"),
            "description": record.get("description"),
            "organism": record.get("organism"),
            "tax_id": safe_int(record.get("tax_id")),
            # Complex fields (JSON serialized)
            "target_component_synonyms": self.serialize_json(
                record.get("target_component_synonyms")
            ),
            "target_component_xrefs": self.serialize_json(
                record.get("target_component_xrefs")
            ),
            "protein_classifications": self.serialize_json(
                record.get("protein_classifications")
            ),
        }

        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # Create entity using helper method
        entity = self._create_entity(
            TargetComponent,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            **business_data,
        )

        # Convert Entity to SilverRecord for storage
        return cast("SilverRecord", self.entity_to_silver_record(entity))
