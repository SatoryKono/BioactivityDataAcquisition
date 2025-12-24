"""ChEMBL Molecule Transformer.

Transforms Bronze records to Silver format (Molecule entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.application.core.transform_utils import (
    extract_and_flatten_fields,
    safe_float,
    safe_int,
)
from bioetl.domain.entities import Molecule
from bioetl.domain.transformations import generate_entity_id

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord

# Field mappings for nested structure flattening
_HIERARCHY_MAPPINGS = {
    "hierarchy_parent_chembl_id": ("parent_chembl_id", None),
    "hierarchy_active_chembl_id": ("active_chembl_id", None),
    "hierarchy_child_chembl_id": ("molecule_chembl_id", None),
}

_STRUCTURE_MAPPINGS = {
    "structure_canonical_smiles": ("canonical_smiles", None),
    "structure_standard_inchi": ("standard_inchi", None),
    "structure_standard_inchi_key": ("standard_inchi_key", None),
}

# Property mappings with type converters
_PROPERTY_MAPPINGS = {
    "property_alogp": ("alogp", safe_float),
    "property_mw_freebase": ("mw_freebase", safe_float),
    "property_full_mwt": ("full_mwt", safe_float),
    "property_hba": ("hba", safe_int),
    "property_hbd": ("hbd", safe_int),
    "property_psa": ("psa", safe_float),
    "property_rtb": ("rtb", safe_int),
    "property_ro5_violations": ("num_lipinski_ro5_violations", safe_int),
    "property_heavy_atoms": ("heavy_atoms", safe_int),
    "property_aromatic_rings": ("aromatic_rings", safe_int),
    "property_qed_weighted": ("qed_weighted", safe_float),
    "property_acd_logd": ("acd_logd", safe_float),
    "property_acd_logp": ("acd_logp", safe_float),
    "property_acd_most_apka": ("acd_most_apka", safe_float),
    "property_acd_most_bpka": ("acd_most_bpka", safe_float),
    "property_full_molformula": ("full_molformula", None),
    "property_ro3_pass": ("ro3_pass", None),
}


class MoleculeTransformer(BaseTransformer):
    """Transforms ChEMBL bronze molecule records to silver."""

    def __init__(self, provider: str = "chembl"):
        super().__init__(provider)

    async def _transform_impl(
        self,
        context: PipelineContext,
        record: BronzeRecord,
    ) -> SilverRecord | None:
        """Transform raw ChEMBL molecule to normalized format using Domain Entity."""
        # Validate required field
        molecule_chembl_id = self._get_required_field(record, "molecule_chembl_id")

        entity_id = generate_entity_id(
            record={"molecule_chembl_id": str(molecule_chembl_id)},
            provider=self.provider,
            id_field="molecule_chembl_id",
        )

        # Extract and flatten complex fields using utility
        hierarchy = extract_and_flatten_fields(
            record.get("molecule_hierarchy"), _HIERARCHY_MAPPINGS
        )
        properties = extract_and_flatten_fields(
            record.get("molecule_properties"), _PROPERTY_MAPPINGS
        )
        structures = extract_and_flatten_fields(
            record.get("molecule_structures"), _STRUCTURE_MAPPINGS
        )

        business_data: dict[str, Any] = {
            # Primary identifier
            "molecule_chembl_id": str(molecule_chembl_id),
            # Core metadata
            "pref_name": record.get("pref_name"),
            "molecule_type": record.get("molecule_type"),
            "structure_type": record.get("structure_type"),
            "max_phase": safe_int(record.get("max_phase")),
            "first_approval": safe_int(record.get("first_approval")),
            # Flags
            "oral": record.get("oral"),
            "parenteral": record.get("parenteral"),
            "topical": record.get("topical"),
            "black_box_warning": safe_int(record.get("black_box_warning")),
            "natural_product": safe_int(record.get("natural_product")),
            "first_in_class": safe_int(record.get("first_in_class")),
            "prodrug": safe_int(record.get("prodrug")),
            "therapeutic_flag": record.get("therapeutic_flag"),
            "withdrawn_flag": record.get("withdrawn_flag"),
            "inorganic_flag": safe_int(record.get("inorganic_flag")),
            "polymer_flag": safe_int(record.get("polymer_flag")),
            "chirality": safe_int(record.get("chirality")),
            "dosed_ingredient": safe_int(record.get("dosed_ingredient")),
            "availability_type": safe_int(record.get("availability_type")),
            # Withdrawn metadata
            "withdrawn_year": safe_int(record.get("withdrawn_year")),
            "withdrawn_country": self.serialize_json(record.get("withdrawn_country")),
            "withdrawn_reason": self.serialize_json(record.get("withdrawn_reason")),
            # USAN naming
            "usan_stem": record.get("usan_stem"),
            "usan_stem_definition": record.get("usan_stem_definition"),
            "usan_substem": record.get("usan_substem"),
            "usan_year": safe_int(record.get("usan_year")),
            # Other metadata
            "helm_notation": record.get("helm_notation"),
            "molecule_species": record.get("molecule_species"),
            # Complex fields (JSON serialized for history)
            "molecule_hierarchy": self.serialize_json(
                record.get("molecule_hierarchy")
            ),
            "molecule_properties": self.serialize_json(
                record.get("molecule_properties")
            ),
            "molecule_structures": self.serialize_json(
                record.get("molecule_structures")
            ),
            "molecule_synonyms": self.serialize_json(
                record.get("molecule_synonyms")
            ),
            "cross_references": self.serialize_json(record.get("cross_references")),
            "atc_classifications": self.serialize_json(
                record.get("atc_classifications")
            ),
            # Flattened fields
            **hierarchy,
            **properties,
            **structures,
        }

        content_hash = self.compute_content_hash(business_data, exclude_none=True)

        # Create entity using helper method
        entity = self._create_entity(
            Molecule,
            context,
            entity_id=entity_id,
            content_hash=content_hash,
            **business_data,
        )

        # Convert Entity to SilverRecord for storage
        return cast("SilverRecord", self.entity_to_silver_record(entity))
