"""ChEMBL Target Component Transformer.

Transforms Bronze records to Silver format (Target Component entity inflation).
Uses declarative field_specs DSL for mapping where applicable.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.field_specs import (
    FieldGroup,
    int_fields,
    map_field_groups,
    simple_fields,
)
from bioetl.application.core.transform_utils import extract_list_field
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import TargetComponent
from bioetl.domain.transformations import safe_int

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


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
        *int_fields("tax_id"),
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
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract TargetComponent business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated component_id value.

        Returns:
            Dictionary of TargetComponent business fields.

        """
        return {
            # Primary identifier (int)
            "component_id": safe_int(primary_id),
            # Declarative field groups
            **map_field_groups(record, _TARGET_COMPONENT_GROUPS),
            # JSON serialization using helper method
            **self.serialize_json_fields(record, _JSON_FIELDS),
            # Flattened fields (extracted from protein_classifications)
            "protein_classification_ids": extract_list_field(
                cast(
                    "list[dict[str, Any]] | None", record.get("protein_classifications")
                ),
                "protein_classification_id",
                safe_int,
            ),
        }
