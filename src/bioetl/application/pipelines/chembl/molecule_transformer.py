"""ChEMBL Molecule Transformer.

Transforms Bronze records to Silver format (Molecule entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.domain.entities import Molecule
from bioetl.domain.transformations import generate_entity_id, safe_float, safe_int

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


class MoleculeTransformer(BaseTransformer):
    """Transforms ChEMBL bronze molecule records to silver."""

    def __init__(self, provider: str = "chembl"):
        """Initialize ChEMBL molecule transformer.

        Args:
            provider: Data provider identifier.
        """
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

        # Extract and flatten complex fields
        hierarchy = self._extract_hierarchy(record.get("molecule_hierarchy"))
        properties = self._extract_properties(record.get("molecule_properties"))
        structures = self._extract_structures(record.get("molecule_structures"))

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

    def _extract_hierarchy(self, data: dict[str, Any] | None) -> dict[str, Any]:
        if not data:
            return {
                "hierarchy_parent_chembl_id": None,
                "hierarchy_active_chembl_id": None,
                "hierarchy_child_chembl_id": None,
            }
        return {
            "hierarchy_parent_chembl_id": data.get("parent_chembl_id"),
            "hierarchy_active_chembl_id": data.get("active_chembl_id"),
            "hierarchy_child_chembl_id": data.get("molecule_chembl_id"),
        }

    def _extract_properties(self, data: dict[str, Any] | None) -> dict[str, Any]:
        if not data:
            return {
                "property_alogp": None,
                "property_mw_freebase": None,
                "property_full_mwt": None,
                "property_hba": None,
                "property_hbd": None,
                "property_psa": None,
                "property_rtb": None,
                "property_ro5_violations": None,
                "property_heavy_atoms": None,
                "property_aromatic_rings": None,
                "property_qed_weighted": None,
                "property_acd_logd": None,
                "property_acd_logp": None,
                "property_acd_most_apka": None,
                "property_acd_most_bpka": None,
                "property_full_molformula": None,
                "property_ro3_pass": None,
            }
        return {
            "property_alogp": safe_float(data.get("alogp")),
            "property_mw_freebase": safe_float(data.get("mw_freebase")),
            "property_full_mwt": safe_float(data.get("full_mwt")),
            "property_hba": safe_int(data.get("hba")),
            "property_hbd": safe_int(data.get("hbd")),
            "property_psa": safe_float(data.get("psa")),
            "property_rtb": safe_int(data.get("rtb")),
            "property_ro5_violations": safe_int(
                data.get("num_lipinski_ro5_violations")
            ),
            "property_heavy_atoms": safe_int(data.get("heavy_atoms")),
            "property_aromatic_rings": safe_int(data.get("aromatic_rings")),
            "property_qed_weighted": safe_float(data.get("qed_weighted")),
            "property_acd_logd": safe_float(data.get("acd_logd")),
            "property_acd_logp": safe_float(data.get("acd_logp")),
            "property_acd_most_apka": safe_float(data.get("acd_most_apka")),
            "property_acd_most_bpka": safe_float(data.get("acd_most_bpka")),
            "property_full_molformula": data.get("full_molformula"),
            "property_ro3_pass": data.get("ro3_pass"),
        }

    def _extract_structures(self, data: dict[str, Any] | None) -> dict[str, Any]:
        if not data:
            return {
                "structure_canonical_smiles": None,
                "structure_standard_inchi": None,
                "structure_standard_inchi_key": None,
            }
        return {
            "structure_canonical_smiles": data.get("canonical_smiles"),
            "structure_standard_inchi": data.get("standard_inchi"),
            "structure_standard_inchi_key": data.get("standard_inchi_key"),
        }
