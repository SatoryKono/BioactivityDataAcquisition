"""ChEMBL Target Component Transformer.

Transforms Bronze records to Silver format (Target Component entity inflation).
Uses declarative field_specs DSL for mapping where applicable.
"""

from __future__ import annotations

from bioetl.domain.types import JsonDict

__all__ = ["TargetComponentTransformer"]


from typing import TYPE_CHECKING, cast

from bioetl.application.core.dict_transformers import extract_list_field
from bioetl.application.core.field_specs import (
    FieldGroup,
    FieldSpec,
    map_field_groups,
    simple_fields,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import TargetComponent
from bioetl.domain.transformations import safe_int
from bioetl.domain.value_objects.taxonomy_id import validate_taxonomy_id

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord, PrimaryId


# JSON fields to serialize
_JSON_FIELDS: tuple[str, ...] = (
    "target_component_synonyms",
    "target_component_xrefs",
    "protein_classifications",
)

# Declarative field group for core metadata
_CORE_METADATA = FieldGroup(
    name="core_metadata",
    fields=(
        *simple_fields("accession", "component_type", "description", "organism"),
        # Standardized to 'taxonomy_id' for NCBI consistency (was 'tax_id')
        FieldSpec("tax_id", target="taxonomy_id", converter=validate_taxonomy_id),
    ),
)

_TARGET_COMPONENT_GROUPS: tuple[FieldGroup, ...] = (_CORE_METADATA,)


class TargetComponentTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze target component records to silver."""

    entity_class = TargetComponent
    primary_id_field = "component_id"

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: PrimaryId,
    ) -> JsonDict:  # Any: transformer record has heterogeneous values
        """Extract TargetComponent business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated component_id value.

        Returns:
            Dictionary of TargetComponent business fields.

        """
        # BronzeRecord is already a JsonDict
        rec = record
        return {
            # Primary identifier (int)
            "component_id": safe_int(primary_id),
            # Declarative field groups (uses BronzeRecord type)
            **map_field_groups(record, _TARGET_COMPONENT_GROUPS),
            # JSON serialization using helper method
            **self.serialize_json_fields(rec, _JSON_FIELDS),
            # Flattened fields (extracted from protein_classifications)
            "protein_classification_ids": self.serialize_json_list(classification_ids)
            if (
                classification_ids := extract_list_field(
                    cast(
                        "list[JsonDict] | None",  # Any: transformer record has heterogeneous values
                        rec.get("protein_classifications"),
                    ),
                    "protein_classification_id",
                    safe_int,
                )
            )
            else None,
            # Primary classification ID (for enricher join key)
            "protein_classification_id": (
                classification_ids[0] if classification_ids else None
            ),
        }
