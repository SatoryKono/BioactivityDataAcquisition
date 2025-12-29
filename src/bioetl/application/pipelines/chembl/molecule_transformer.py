"""ChEMBL Molecule Transformer.

Transforms Bronze records to Silver format (Molecule entity inflation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, cast

from bioetl.application.core.transform_utils import flatten_nested_dict
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import Molecule
from bioetl.domain.transformations import safe_float, safe_int

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


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


class MoleculeTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze molecule records to silver."""

    entity_class = Molecule
    primary_id_field = "molecule_chembl_id"

    def _map_core_metadata(self, record: BronzeRecord) -> dict[str, Any]:
        """Map core molecule metadata fields."""
        return {
            "pref_name": record.get("pref_name"),
            "molecule_type": record.get("molecule_type"),
            "structure_type": record.get("structure_type"),
            "max_phase": safe_int(record.get("max_phase")),
            "first_approval": safe_int(record.get("first_approval")),
        }

    def _map_molecule_flags(self, record: BronzeRecord) -> dict[str, Any]:
        """Map molecule boolean/flag fields."""
        return {
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
        }

    def _map_additional_metadata(self, record: BronzeRecord) -> dict[str, Any]:
        """Map USAN naming and other metadata fields."""
        return {
            "usan_stem": record.get("usan_stem"),
            "usan_stem_definition": record.get("usan_stem_definition"),
            "usan_substem": record.get("usan_substem"),
            "usan_year": safe_int(record.get("usan_year")),
            "helm_notation": record.get("helm_notation"),
            "molecule_species": record.get("molecule_species"),
        }

    def _map_complex_fields(self, record: BronzeRecord) -> dict[str, Any]:
        """Map complex JSON-serialized fields."""
        return {
            "molecule_hierarchy": self.serialize_json(record.get("molecule_hierarchy")),
            "molecule_properties": self.serialize_json(
                record.get("molecule_properties")
            ),
            "molecule_structures": self.serialize_json(
                record.get("molecule_structures")
            ),
            "molecule_synonyms": self.serialize_json(record.get("molecule_synonyms")),
            "cross_references": self.serialize_json(record.get("cross_references")),
            "atc_classifications": self.serialize_json(
                record.get("atc_classifications")
            ),
        }

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: Any,
    ) -> dict[str, Any]:
        """Extract Molecule business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated molecule_chembl_id value.

        Returns:
            Dictionary of Molecule business fields.

        """
        return {
            "molecule_chembl_id": str(primary_id),
            **self._map_core_metadata(record),
            **self._map_molecule_flags(record),
            **self._map_additional_metadata(record),
            **self._map_complex_fields(record),
            **_extract_hierarchy(
                cast("dict[str, Any] | None", record.get("molecule_hierarchy"))
            ),
            **_extract_properties(
                cast("dict[str, Any] | None", record.get("molecule_properties"))
            ),
            **_extract_structures(
                cast("dict[str, Any] | None", record.get("molecule_structures"))
            ),
        }
