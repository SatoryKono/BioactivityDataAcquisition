"""ChEMBL Molecule Transformer.

Transforms Bronze records to Silver format (Molecule entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.application.core.transform_utils import flatten_nested_dict
from bioetl.domain.entities import Molecule
from bioetl.domain.transformations import generate_entity_id, safe_float, safe_int

if TYPE_CHECKING:
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.types import BronzeRecord, SilverRecord


# Field mappings for molecule nested structures
_HIERARCHY_FIELDS: dict[str, Any] = {
    "parent_chembl_id": None,
    "active_chembl_id": None,
    "molecule_chembl_id": None,
}

_PROPERTIES_FIELDS: dict[str, Any] = {
    "alogp": safe_float,
    "mw_freebase": safe_float,
    "full_mwt": safe_float,
    "hba": safe_int,
    "hbd": safe_int,
    "psa": safe_float,
    "rtb": safe_int,
    "num_ro5_violations": safe_int,  # ChEMBL API field name (not num_lipinski_ro5_violations)
    "heavy_atoms": safe_int,
    "aromatic_rings": safe_int,
    "qed_weighted": safe_float,
    "full_molformula": None,
    "ro3_pass": None,
    # Note: acd_logd, acd_logp, acd_most_apka, acd_most_bpka were removed
    # as they are not available in the public ChEMBL API
}

_STRUCTURES_FIELDS: dict[str, Any] = {
    "canonical_smiles": None,
    "standard_inchi": None,
    "standard_inchi_key": None,
}


def _extract_hierarchy(data: dict[str, Any] | None) -> dict[str, Any]:
    """Extract and rename hierarchy fields using flatten_nested_dict."""
    result = flatten_nested_dict(data, "hierarchy_", _HIERARCHY_FIELDS)
    # Rename molecule_chembl_id -> child_chembl_id for clarity
    result["hierarchy_child_chembl_id"] = result.pop("hierarchy_molecule_chembl_id")
    return result


def _extract_properties(data: dict[str, Any] | None) -> dict[str, Any]:
    """Extract and rename properties fields using flatten_nested_dict."""
    result = flatten_nested_dict(data, "property_", _PROPERTIES_FIELDS)
    # Rename num_ro5_violations -> ro5_violations for consistency
    result["property_ro5_violations"] = result.pop("property_num_ro5_violations")
    return result


def _extract_structures(data: dict[str, Any] | None) -> dict[str, Any]:
    """Extract structures fields using flatten_nested_dict."""
    return flatten_nested_dict(data, "structure_", _STRUCTURES_FIELDS)


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

        # Extract and flatten complex fields via module-level functions
        hierarchy = _extract_hierarchy(record.get("molecule_hierarchy"))
        properties = _extract_properties(record.get("molecule_properties"))
        structures = _extract_structures(record.get("molecule_structures"))

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
            # Note: withdrawn_year, withdrawn_country, withdrawn_reason are not available
            # in the /molecule endpoint. Use /drug_warning endpoint for detailed info.
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
