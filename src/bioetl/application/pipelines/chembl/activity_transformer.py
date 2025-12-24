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
        """Initialize ChEMBL activity transformer.

        Args:
            provider: Data provider identifier.

        """
        super().__init__(provider)

    def _extract_ligand_efficiency(
        self,
        le_data: dict[str, Any] | None,
    ) -> dict[str, float | None]:
        """Extract ligand efficiency metrics from nested data.

        Args:
            le_data: Nested ligand efficiency dictionary from ChEMBL API.

        Returns:
            Flattened dictionary with ligand_efficiency_ prefixed keys.

        """
        return flatten_nested_dict(le_data, "ligand_efficiency_", _LIGAND_EFFICIENCY_FIELDS)

    def _extract_action_type(
        self,
        action_data: dict[str, Any] | None,
    ) -> dict[str, str | None]:
        """Extract action type fields from nested data.

        Args:
            action_data: Nested action_type dictionary from ChEMBL API.
                Expected structure: {"action_type": "INHIBITOR", "description": "...", "parent_type": "..."}

        Returns:
            Flattened dictionary with action_type_ prefixed keys:
                - action_type_action_type: Type of action (INHIBITOR, AGONIST, etc.)
                - action_type_description: Description of the action type
                - action_type_parent_type: Higher-level grouping (nullable)

        """
        return flatten_nested_dict(action_data, "action_type_", _ACTION_TYPE_FIELDS)

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL activity to normalized format using Domain Entity."""
        # Validate required fields
        activity_id = self._get_required_field(record, "activity_id")
        molecule_id = self._get_required_field(record, "molecule_chembl_id")

        entity_id = generate_entity_id(
            record={"activity_id": str(activity_id)},
            provider=self.provider,
            id_field="activity_id",
        )

        # Map ALL raw fields to Entity fields
        business_data: dict[str, Any] = {
            # Primary identifier
            "activity_id": str(activity_id),
            # Core identifiers
            "molecule_chembl_id": str(molecule_id),
            "target_chembl_id": record.get("target_chembl_id"),
            "assay_chembl_id": record.get("assay_chembl_id"),
            "document_chembl_id": record.get("document_chembl_id"),
            "record_id": safe_int(record.get("record_id")),
            "src_id": safe_int(record.get("src_id")),
            # Molecule data
            "canonical_smiles": record.get("canonical_smiles"),
            "molecule_pref_name": record.get("molecule_pref_name"),
            "parent_molecule_chembl_id": record.get("parent_molecule_chembl_id"),
            # Target data
            "target_pref_name": record.get("target_pref_name"),
            "target_organism": record.get("target_organism"),
            "target_tax_id": record.get("target_tax_id"),
            # Assay data
            "assay_type": record.get("assay_type"),
            "assay_description": record.get("assay_description"),
            "assay_variant_accession": record.get("assay_variant_accession"),
            "assay_variant_mutation": record.get("assay_variant_mutation"),
            # BAO annotations
            "bao_endpoint": record.get("bao_endpoint"),
            "bao_format": record.get("bao_format"),
            "bao_label": record.get("bao_label"),
            # Raw activity values
            "type": record.get("type"),
            "value": safe_float(record.get("value")),
            "units": record.get("units"),
            "relation": record.get("relation"),
            "upper_value": safe_float(record.get("upper_value")),
            "text_value": record.get("text_value"),
            # Standardized activity values
            "standard_type": record.get("standard_type"),
            "standard_value": safe_float(record.get("standard_value")),
            "standard_units": record.get("standard_units"),
            "standard_relation": record.get("standard_relation"),
            "standard_upper_value": safe_float(record.get("standard_upper_value")),
            "standard_text_value": record.get("standard_text_value"),
            "standard_flag": safe_int(record.get("standard_flag")),
            # Derived metrics
            "pchembl_value": safe_float(record.get("pchembl_value")),
            # Ligand efficiency metrics (flattened via transform_utils)
            **flatten_nested_dict(
                record.get("ligand_efficiency"),
                "ligand_efficiency_",
                _LIGAND_EFFICIENCY_FIELDS,
            ),
            # Units ontology
            "qudt_units": record.get("qudt_units"),
            "uo_units": record.get("uo_units"),
            # Document data
            "document_journal": record.get("document_journal"),
            "document_year": safe_int(record.get("document_year")),
            # Quality annotations
            "activity_comment": record.get("activity_comment"),
            "data_validity_comment": record.get("data_validity_comment"),
            "data_validity_description": record.get("data_validity_description"),
            "potential_duplicate": safe_int(record.get("potential_duplicate")),
            # Action type (flattened from ChEMBL API nested structure)
            **self._extract_action_type(record.get("action_type")),
            # Activity properties
            "activity_properties": self.serialize_json(
                record.get("activity_properties")
            ),
            "toid": safe_int(record.get("toid")),
        }

        # Generate content hash based on business data (exclude None values)
        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # Create entity using helper method
        entity = self._create_entity(
            Activity,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            **business_data,
        )

        # Convert Entity to SilverRecord for storage
        return cast("SilverRecord", self.entity_to_silver_record(entity))
