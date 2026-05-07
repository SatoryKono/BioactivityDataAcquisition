"""ChEMBL Subcellular Fraction Transformer.

Transforms Assay records to extract and deduplicate subcellular fraction values.
This is a derived entity transformer - it extracts unique assay_subcellular_fraction
values from Assay API responses and creates a lookup/reference table.

Uses declarative field_specs DSL for mapping.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import TransformationError
from bioetl.application.core.entity_id import compute_subcellular_fraction_entity_id
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities.chembl_subcellular_fraction import SubcellularFraction
from bioetl.domain.types import JsonDict

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

    async def transform_pre_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> PreSilverRecord | None:
        """Build an intermediate subcellular-fraction payload for finalization."""
        del context, index
        resolved = _resolve_subcellular_fraction_payload(self, record)
        if resolved is None:
            return None
        _, business_data = resolved
        return self._stage_optional_normalized_business_data(
            business_data=business_data,
            resolve_entity_id=lambda data: _resolve_subcellular_fraction_entity_id(
                self, data
            ),
        )

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Override base implementation to use subcellular_fraction as entity_id."""
        resolved = _resolve_subcellular_fraction_payload(self, record)
        if resolved is None:
            return None
        _, business_data = resolved
        return self._transform_optional_normalized_business_data(
            context=context,
            index=index,
            business_data=business_data,
            resolve_entity_id=lambda data: _resolve_subcellular_fraction_entity_id(
                self, data
            ),
        )

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: PrimaryId,
    ) -> JsonDict:  # Any: transformer record has heterogeneous values
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
        return compute_subcellular_fraction_entity_id(subcellular_fraction)

    def extract_fraction_from_assay(
        self,
        record: BronzeRecord,
    ) -> JsonDict | None:  # Any: transformer record has heterogeneous values
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
            "subcellular_fraction_raw": fraction,
            "subcellular_fraction": fraction,
            "example_assay_id": str(assay_id) if assay_id else None,
            "assay_count": 1,
        }


def _resolve_subcellular_fraction_payload(
    transformer: SubcellularFractionTransformer,
    record: BronzeRecord,
) -> tuple[PrimaryId, JsonDict] | None:
    """Resolve primary id and business data from direct or assay-derived records."""
    extracted_from_assay = transformer.extract_fraction_from_assay(record)
    primary_value = record.get(transformer.primary_id_field)
    if extracted_from_assay and primary_value is None:
        primary_id = cast("PrimaryId", extracted_from_assay["subcellular_fraction"])
        return primary_id, extracted_from_assay
    try:
        primary_id = cast(
            "PrimaryId",
            transformer._get_required_field(record, transformer.primary_id_field),
        )
    except TransformationError:
        return None
    return primary_id, transformer._extract_business_data(record, primary_id)


def _resolve_subcellular_fraction_entity_id(
    transformer: SubcellularFractionTransformer,
    business_data: JsonDict,
) -> str:
    """Resolve entity id from canonical normalized fraction business data."""
    return transformer.compute_fraction_entity_id(
        str(business_data.get("subcellular_fraction", ""))
    )
__all__ = ["SubcellularFractionTransformer"]
