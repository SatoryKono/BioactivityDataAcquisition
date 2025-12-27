"""ChEMBL Target Component Transformer.

Transforms Bronze records to Silver format (Target Component entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.transform_utils import extract_list_field
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import TargetComponent
from bioetl.domain.transformations import safe_int

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


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
            # Primary identifier
            "component_id": safe_int(primary_id),
            # Core metadata
            "accession": record.get("accession"),
            "component_type": record.get("component_type"),
            "description": record.get("description"),
            "organism": record.get("organism"),
            "tax_id": safe_int(record.get("tax_id")),
            # Complex fields (JSON serialized for forensic purposes)
            "target_component_synonyms": self.serialize_json(
                record.get("target_component_synonyms")
            ),
            "target_component_xrefs": self.serialize_json(
                record.get("target_component_xrefs")
            ),
            "protein_classifications": self.serialize_json(
                record.get("protein_classifications")
            ),
            # Flattened fields (extracted from protein_classifications)
            "protein_classification_ids": extract_list_field(
                cast("list[dict[str, Any]] | None", record.get("protein_classifications")),
                "protein_classification_id",
                safe_int,
            ),
        }
