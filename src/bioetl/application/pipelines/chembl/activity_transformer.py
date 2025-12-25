"""ChEMBL Activity Transformer.

Transforms Bronze records to Silver format (Activity entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.application.core.transform_utils import flatten_nested_dict
from bioetl.domain.entities import Activity
from bioetl.domain.transformations import generate_entity_id, safe_float, safe_int

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


# Mapping for ligand efficiency fields extraction
_LIGAND_EFFICIENCY_FIELDS: dict[str, Any] = {
    "bei": safe_float,
    "le": safe_float,
    "lle": safe_float,
    "sei": safe_float,
}

# Mapping for action type fields extraction (from ChEMBL nested structure)
_ACTION_TYPE_FIELDS: dict[str, Any] = {
    "action_type": None,  # str, no converter needed
    "description": None,
    "parent_type": None,
}


class ActivityTransformer(BaseTransformer):
    """Transforms ChEMBL bronze records to silver."""

    def __init__(self, provider: str = "chembl"):
        """Initialize ChEMBL activity transformer."""
        super().__init__(provider)

    def _map_core_identifiers(
        self, record: BronzeRecord, activity_id: Any, molecule_id: Any
    ) -> dict[str, Any]:
        """Map core identifier fields from record."""
        return {
            "activity_id": str(activity_id),
            "molecule_chembl_id": str(molecule_id),
            "target_chembl_id": record.get("target_chembl_id"),
            "assay_chembl_id": record.get("assay_chembl_id"),
            "document_chembl_id": record.get("document_chembl_id"),
            "record_id": safe_int(record.get("record_id")),
            "src_id": safe_int(record.get("src_id")),
        }

    def _map_molecule_target_assay(self, record: BronzeRecord) -> dict[str, Any]:
        """Map molecule, target, and assay related fields."""
        return {
            "canonical_smiles": record.get("canonical_smiles"),
            "molecule_pref_name": record.get("molecule_pref_name"),
            "parent_molecule_chembl_id": record.get("parent_molecule_chembl_id"),
            "target_pref_name": record.get("target_pref_name"),
            "target_organism": record.get("target_organism"),
            "target_tax_id": record.get("target_tax_id"),
            "assay_type": record.get("assay_type"),
            "assay_description": record.get("assay_description"),
            "assay_variant_accession": record.get("assay_variant_accession"),
            "assay_variant_mutation": record.get("assay_variant_mutation"),
            "bao_endpoint": record.get("bao_endpoint"),
            "bao_format": record.get("bao_format"),
            "bao_label": record.get("bao_label"),
        }

    def _map_activity_values(self, record: BronzeRecord) -> dict[str, Any]:
        """Map raw and standardized activity values."""
        return {
            "type": record.get("type"),
            "value": safe_float(record.get("value")),
            "units": record.get("units"),
            "relation": record.get("relation"),
            "upper_value": safe_float(record.get("upper_value")),
            "text_value": record.get("text_value"),
            "standard_type": record.get("standard_type"),
            "standard_value": safe_float(record.get("standard_value")),
            "standard_units": record.get("standard_units"),
            "standard_relation": record.get("standard_relation"),
            "standard_upper_value": safe_float(record.get("standard_upper_value")),
            "standard_text_value": record.get("standard_text_value"),
            "standard_flag": safe_int(record.get("standard_flag")),
            "pchembl_value": safe_float(record.get("pchembl_value")),
            **flatten_nested_dict(
                record.get("ligand_efficiency"),
                "ligand_efficiency_",
                _LIGAND_EFFICIENCY_FIELDS,
            ),
            "qudt_units": record.get("qudt_units"),
            "uo_units": record.get("uo_units"),
        }

    def _map_quality_annotations(self, record: BronzeRecord) -> dict[str, Any]:
        """Map document and quality annotation fields."""
        return {
            "document_journal": record.get("document_journal"),
            "document_year": safe_int(record.get("document_year")),
            "activity_comment": record.get("activity_comment"),
            "data_validity_comment": record.get("data_validity_comment"),
            "data_validity_description": record.get("data_validity_description"),
            "potential_duplicate": safe_int(record.get("potential_duplicate")),
            **flatten_nested_dict(
                record.get("action_type"), "action_type_", _ACTION_TYPE_FIELDS
            ),
            "activity_properties": self.serialize_json(
                record.get("activity_properties")
            ),
            "toid": safe_int(record.get("toid")),
        }

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL activity to normalized format."""
        activity_id = self._get_required_field(record, "activity_id")
        molecule_id = self._get_required_field(record, "molecule_chembl_id")

        entity_id = generate_entity_id(
            record={"activity_id": str(activity_id)},
            provider=self.provider,
            id_field="activity_id",
        )

        business_data: dict[str, Any] = {
            **self._map_core_identifiers(record, activity_id, molecule_id),
            **self._map_molecule_target_assay(record),
            **self._map_activity_values(record),
            **self._map_quality_annotations(record),
        }

        content_hash = self.compute_content_hash(business_data, exclude_none=True)
        entity = self._create_entity(
            Activity,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            **business_data,
        )

        return cast("SilverRecord", self.entity_to_silver_record(entity))
