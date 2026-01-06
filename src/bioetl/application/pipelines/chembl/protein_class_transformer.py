"""ChEMBL Protein Classification Transformer.

Transforms Bronze records to Silver format (ProteinClassification entity inflation).
Uses declarative field_specs DSL for mapping.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

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
    from bioetl.domain.types import BronzeRecord


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

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
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
