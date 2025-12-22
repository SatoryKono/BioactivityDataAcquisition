"""ChEMBL Assay Transformer.

Transforms Bronze records to Silver format (Assay entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import Assay
from bioetl.domain.transformations import (
    generate_entity_id,
    safe_int,
)

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


class AssayTransformer(BaseTransformer):
    """Transforms ChEMBL assay bronze records to silver."""

    def __init__(self, provider: str = "chembl"):
        super().__init__(provider)

    async def transform(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL assay to normalized format using Domain Entity."""
        assay_chembl_id = record.get("assay_chembl_id")

        if not assay_chembl_id:
            return None

        try:
            entity_id = generate_entity_id(
                record={"assay_chembl_id": str(assay_chembl_id)},
                provider=self.provider,
                id_field="assay_chembl_id",
            )

            # Map ALL raw fields to Entity fields
            business_data: dict[str, Any] = {
                # Primary identifier
                "assay_chembl_id": str(assay_chembl_id),
                # Core identifiers
                "target_chembl_id": record.get("target_chembl_id"),
                "document_chembl_id": record.get("document_chembl_id"),
                "cell_chembl_id": record.get("cell_chembl_id"),
                "tissue_chembl_id": record.get("tissue_chembl_id"),
                "src_id": safe_int(record.get("src_id")),
                "src_assay_id": record.get("src_assay_id"),
                "aidx": record.get("aidx"),
                # Assay classification
                "assay_type": record.get("assay_type"),
                "assay_type_description": record.get("assay_type_description"),
                "assay_category": record.get("assay_category"),
                "assay_test_type": record.get("assay_test_type"),
                "assay_group": record.get("assay_group"),
                # Biological context
                "assay_organism": record.get("assay_organism"),
                "assay_tax_id": safe_int(record.get("assay_tax_id")),
                "assay_cell_type": record.get("assay_cell_type"),
                "assay_tissue": record.get("assay_tissue"),
                "assay_strain": record.get("assay_strain"),
                "assay_subcellular_fraction": record.get("assay_subcellular_fraction"),
                # BAO annotations
                "bao_format": record.get("bao_format"),
                "bao_label": record.get("bao_label"),
                # Description and confidence
                "description": record.get("description"),
                "confidence_score": safe_int(record.get("confidence_score")),
                "confidence_description": record.get("confidence_description"),
                "relationship_type": record.get("relationship_type"),
                "relationship_description": record.get("relationship_description"),
                # Variant information
                "variant_sequence": self.serialize_json(record.get("variant_sequence")),
                # Complex fields (stored as JSON strings)
                "assay_classifications": self.serialize_json(
                    record.get("assay_classifications")
                ),
                "assay_parameters": self.serialize_json(record.get("assay_parameters")),
            }

            # Generate content hash based on business data (exclude None values)
            # Note: Original used explicit dict comprehension, but compute_content_hash
            # with exclude_none=True is equivalent
            content_hash = self.compute_content_hash(business_data, exclude_none=True)

            entity = Assay(
                entity_id=entity_id,
                content_hash=content_hash,
                run_id=context.run_id,
                run_type=context.run_type,
                source_batch_id=None,
                **business_data,
            )

        except ValueError as e:
            context.logger.warning(
                "entity_validation_failed",
                error=str(e),
                assay_chembl_id=assay_chembl_id,
            )
            return None

        # Convert Entity to SilverRecord for storage
        silver_record = self.entity_to_silver_record(entity)

        return cast("SilverRecord", silver_record)
