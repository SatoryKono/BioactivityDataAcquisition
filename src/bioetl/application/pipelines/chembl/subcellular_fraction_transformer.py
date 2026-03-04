"""ChEMBL Subcellular Fraction Transformer.

Transforms Assay records to extract and deduplicate subcellular fraction values.
This is a derived entity transformer - it extracts unique assay_subcellular_fraction
values from Assay API responses and creates a lookup/reference table.

Uses declarative field_specs DSL for mapping.
"""

from __future__ import annotations

import hashlib
from typing import TYPE_CHECKING, Any, cast

from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities.chembl_subcellular_fraction import SubcellularFraction

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, PrimaryId, SilverRecord


class SubcellularFractionTransformer(BaseChemblTransformer):
    """Transforms ChEMBL assay records to extract unique subcellular fraction records.

    This transformer extracts unique subcellular_fraction values from Assay
    API responses, creating a lookup/reference table for biological context.

    Subcellular fractions describe the cellular compartment or preparation
    used in bioassay experiments (e.g., "Microsomes", "Cytosol", "Mitochondria").

    Entity ID is computed as SHA256 hash of normalized subcellular_fraction name.

    Note: This transformer expects pre-extracted records from
    SubcellularFractionDataSource, which handles deduplication at fetch level.
    """

    entity_class = SubcellularFraction
    primary_id_field = "subcellular_fraction"

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Override base implementation to use subcellular_fraction as entity_id.

        SubcellularFraction is a derived entity with single-field primary key.
        The entity_id is computed from the normalized subcellular_fraction name.

        If record contains pre-computed entity_id (from SubcellularFractionDataSource),
        use it directly. Otherwise, compute entity_id from subcellular_fraction.

        Args:
            context: Pipeline context with run_id, run_type, logger.
            record: Bronze record (pre-extracted fraction or raw assay).
            index: Sequential index of the record in the pipeline run.

        Returns:
            SilverRecord if transformation successful, None if skipped.

        """
        # 1. Validate primary ID (subcellular_fraction)
        primary_id = cast(
            "PrimaryId",
            self._get_required_field(record, self.primary_id_field),
        )
        if not primary_id:
            return None

        # 2. Extract business data
        business_data = self._extract_business_data(record, primary_id)

        # 3. Compute entity_id
        # Priority: pre-computed entity_id from record > computed from subcellular_fraction
        pre_computed_id = record.get("entity_id")
        if pre_computed_id:
            entity_id = str(pre_computed_id)
        else:
            entity_id = self.compute_fraction_entity_id(str(primary_id))

        # 4. Compute content hash
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # 5. Create domain entity
        entity = self._create_entity(
            self.entity_class,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            index=index,
            **business_data,
        )

        # 6. Convert to SilverRecord
        return cast("SilverRecord", self.entity_to_silver_record(entity))

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: PrimaryId,
    ) -> dict[str, Any]:  # Any: transformer record has heterogeneous values
        """Extract subcellular fraction data from the record.

        Handles two cases:
        1. Pre-extracted fraction records (from SubcellularFractionDataSource) - pass through
        2. Raw assay records - extract subcellular_fraction field

        Args:
            record: Bronze record (either fraction record or assay record).
            primary_id: Validated subcellular_fraction value.

        Returns:
            Dictionary of fraction business fields.

        """
        # Normalize the fraction name
        fraction = str(primary_id).strip()

        # Get optional fields
        assay_count = record.get("assay_count")
        example_assay = record.get("example_assay_id")

        return {
            "subcellular_fraction": fraction,
            "assay_count": int(
                cast(Any, assay_count)  # Any: cast for nullable numeric coercion
            )  # Any: cast for nullable numeric coercion
            if assay_count is not None
            else None,
            "example_assay_id": (str(example_assay).strip() if example_assay else None),
        }

    def compute_fraction_entity_id(
        self,
        subcellular_fraction: str,
    ) -> str:
        """Compute entity ID for a subcellular fraction.

        Entity ID is SHA256 hash of: subcellular_fraction:normalized_name

        Args:
            subcellular_fraction: Subcellular fraction name (will be normalized).

        Returns:
            Entity ID string (first 16 chars of SHA256 hex digest).

        """
        normalized = (
            subcellular_fraction.lower().strip() if subcellular_fraction else ""
        )
        composite = f"subcellular_fraction:{normalized}"
        return hashlib.sha256(composite.encode()).hexdigest()[:16]

    def extract_fraction_from_assay(
        self,
        record: BronzeRecord,
    ) -> dict[str, Any] | None:  # Any: transformer record has heterogeneous values
        """Extract subcellular fraction from a raw Assay record.

        This method is used when processing raw assay records directly
        (without SubcellularFractionDataSource wrapper).

        Args:
            record: Raw Bronze record from ChEMBL API /assay endpoint.

        Returns:
            Dictionary of fraction fields if assay_subcellular_fraction is present,
            None otherwise.

        """
        raw_fraction = record.get("assay_subcellular_fraction")
        if not raw_fraction:
            return None

        fraction = str(raw_fraction).strip()
        if not fraction:
            return None

        assay_id = record.get("assay_id") or record.get("assay_chembl_id")

        return {
            "subcellular_fraction": fraction,
            "example_assay_id": str(assay_id) if assay_id else None,
            "assay_count": 1,
        }


__all__ = ["SubcellularFractionTransformer"]
