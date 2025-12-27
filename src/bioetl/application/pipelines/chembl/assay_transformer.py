"""ChEMBL Assay Transformer.

Transforms Bronze records to Silver format (Assay entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from bioetl.application.core.transform_utils import flatten_nested_dict
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import Assay
from bioetl.domain.transformations import (
    safe_float,
    safe_int,
    safe_str,
)

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


# Mapping for variant sequence fields extraction (from ChEMBL nested structure)
# Use safe_str for fields that might come as int from API but need string in schema
_VARIANT_FIELDS: dict[str, Any] = {
    "accession": safe_str,  # UniProt accession, always string
    "isoform": safe_str,  # May come as int (e.g., 1, 2) from API
    "mutation": safe_str,  # Mutation description
    "organism": safe_str,  # Organism name
    "sequence": safe_str,  # Amino acid sequence
    "tax_id": safe_int,  # NCBI Taxonomy ID, always int
}


def _extract_variant(data: dict[str, Any] | None) -> dict[str, Any]:
    """Extract variant sequence fields using flatten_nested_dict.

    Args:
        data: Nested variant_sequence dictionary from ChEMBL API.
            Expected structure: {"accession": "P12345", "mutation": "V600E", ...}

    Returns:
        Flattened dictionary with variant_ prefixed keys:
            - variant_accession
            - variant_isoform
            - variant_mutation
            - variant_organism
            - variant_sequence
            - variant_tax_id

    """
    return flatten_nested_dict(data, "variant_", _VARIANT_FIELDS)


class AssayTransformer(BaseChemblTransformer):
    """Transforms ChEMBL assay bronze records to silver."""

    entity_class = Assay
    primary_id_field = "assay_chembl_id"

    def _map_core_identifiers(
        self, record: BronzeRecord, assay_chembl_id: Any
    ) -> dict[str, Any]:
        """Map core identifier fields."""
        return {
            "assay_chembl_id": str(assay_chembl_id),
            "target_chembl_id": record.get("target_chembl_id"),
            "document_chembl_id": record.get("document_chembl_id"),
            "cell_chembl_id": record.get("cell_chembl_id"),
            "tissue_chembl_id": record.get("tissue_chembl_id"),
            "src_id": safe_int(record.get("src_id")),
            "src_assay_id": record.get("src_assay_id"),
            "aidx": record.get("aidx"),
        }

    def _map_classification_fields(self, record: BronzeRecord) -> dict[str, Any]:
        """Map assay classification fields."""
        return {
            "assay_type": record.get("assay_type"),
            "assay_type_description": record.get("assay_type_description"),
            "assay_category": record.get("assay_category"),
            "assay_test_type": record.get("assay_test_type"),
            "assay_group": record.get("assay_group"),
        }

    def _map_biological_context(self, record: BronzeRecord) -> dict[str, Any]:
        """Map biological context and BAO annotation fields."""
        return {
            "assay_organism": record.get("assay_organism"),
            "assay_tax_id": safe_int(record.get("assay_tax_id")),
            "assay_cell_type": record.get("assay_cell_type"),
            "assay_tissue": record.get("assay_tissue"),
            "assay_strain": record.get("assay_strain"),
            "assay_subcellular_fraction": record.get("assay_subcellular_fraction"),
            "bao_format": record.get("bao_format"),
            "bao_label": record.get("bao_label"),
        }

    def _map_metadata_fields(self, record: BronzeRecord) -> dict[str, Any]:
        """Map description, confidence, and additional metadata fields."""
        return {
            "description": record.get("description"),
            "confidence_score": safe_int(record.get("confidence_score")),
            "confidence_description": record.get("confidence_description"),
            "relationship_type": record.get("relationship_type"),
            "relationship_description": record.get("relationship_description"),
            "assay_pref_name": record.get("assay_pref_name"),
            "score": safe_float(record.get("score")),
            **_extract_variant(record.get("variant_sequence")),
            "variant_sequence_json": self.serialize_json(
                record.get("variant_sequence")
            ),
            "assay_classifications": self.serialize_json(
                record.get("assay_classifications")
            ),
            "assay_parameters": self.serialize_json(record.get("assay_parameters")),
        }

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract Assay business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated assay_chembl_id value.

        Returns:
            Dictionary of Assay business fields.

        """
        return {
            **self._map_core_identifiers(record, primary_id),
            **self._map_classification_fields(record),
            **self._map_biological_context(record),
            **self._map_metadata_fields(record),
        }
