"""ChEMBL Protein Classification Transformer.

Transforms Bronze records to Silver format (ProteinClassification entity inflation).
Uses declarative field_specs DSL for mapping.
"""

from __future__ import annotations

from bioetl.domain.types import JsonDict

__all__ = ["ProteinClassTransformer"]


from typing import TYPE_CHECKING

from bioetl.application.core.field_specs import (
    FieldGroup,
    int_fields,
    map_field_groups,
    simple_fields,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import ProteinClassification
from bioetl.domain.transformations import safe_int

if TYPE_CHECKING:
    from bioetl.application.core.pre_silver_record import PreSilverRecord
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, PrimaryId, SilverRecord


# Declarative field groups for ProteinClassification entity
_HIERARCHY = FieldGroup(
    name="hierarchy",
    fields=int_fields("parent_id", "class_level"),
)

_CLASSIFICATION_DATA = FieldGroup(
    name="classification_data",
    fields=simple_fields(
        "pref_name",
        "short_name",
        "protein_class_desc",
        "definition",
    ),
)

_METADATA = FieldGroup(
    name="metadata",
    fields=int_fields("sort_order", "replaced_by", "downgraded"),
)

_PROTEIN_CLASS_GROUPS: tuple[FieldGroup, ...] = (
    _HIERARCHY,
    _CLASSIFICATION_DATA,
    _METADATA,
)


class ProteinClassTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze protein_class records to silver.

    Handles hierarchical protein classification data.
    Primary key is protein_class_id (integer).
    """

    entity_class = ProteinClassification
    primary_id_field = "protein_class_id"

    @staticmethod
    def _should_skip_record(record: BronzeRecord) -> bool:
        """Skip the synthetic ChEMBL root node that violates domain invariants."""
        protein_class_id = safe_int(record.get("protein_class_id"))
        return protein_class_id is not None and protein_class_id <= 0

    async def transform_pre_silver(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> PreSilverRecord | None:
        """Skip ChEMBL's root classification before entity inflation."""
        if self._should_skip_record(record):
            return None
        return await super().transform_pre_silver(context, record, index)

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
        index: int,
    ) -> SilverRecord | None:
        """Skip invalid root classifications in legacy direct-transform flows."""
        if self._should_skip_record(record):
            return None
        return await super()._transform_impl(context, record, index)

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: PrimaryId,
    ) -> JsonDict:  # Any: transformer record has heterogeneous values
        """Extract ProteinClassification business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated protein_class_id value.

        Returns:
            Dictionary of ProteinClassification business fields.

        """
        return {
            # Primary identifier (int)
            "protein_class_id": safe_int(primary_id),
            # Declarative field groups
            **map_field_groups(record, _PROTEIN_CLASS_GROUPS),
        }
