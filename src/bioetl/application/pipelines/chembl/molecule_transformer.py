"""ChEMBL Molecule Transformer.

Transforms Bronze records to Silver format (Molecule entity inflation).
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
from bioetl.application.core.transform_utils import flatten_nested_dict
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import Molecule
from bioetl.domain.transformations import safe_float, safe_int
from bioetl.domain.value_objects import SMILES, InChIKey

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord


# Field mappings for molecule nested structures
_HIERARCHY_FIELDS: dict[str, Any] = {
    "parent_chembl_id": None,
    "active_chembl_id": None,
    "molecule_chembl_id": None,
}

# Rename mapping for hierarchy fields (molecule_chembl_id -> child_chembl_id)
_HIERARCHY_RENAMES: dict[str, str] = {
    "hierarchy_molecule_chembl_id": "hierarchy_child_chembl_id",
}

_PROPERTIES_FIELDS: dict[str, Any] = {
    "alogp": safe_float,
    "mw_freebase": safe_float,
    "full_mwt": safe_float,
    "hba": safe_int,
    "hbd": safe_int,
    "psa": safe_float,
    "rtb": safe_int,
    "num_ro5_violations": safe_int,
    "heavy_atoms": safe_int,
    "aromatic_rings": safe_int,
    "qed_weighted": safe_float,
    "full_molformula": None,
    "ro3_pass": None,
}

# Rename mapping for properties fields (num_ro5_violations -> ro5_violations)
_PROPERTIES_RENAMES: dict[str, str] = {
    "property_num_ro5_violations": "property_ro5_violations",
}

_STRUCTURES_FIELDS: dict[str, Any] = {
    "canonical_smiles": None,
    "standard_inchi": None,
    "standard_inchi_key": None,
}

# Rename mapping for structures fields (standard_inchi_key -> inchi_key for PubChem consistency)
_STRUCTURES_RENAMES: dict[str, str] = {
    "standard_inchi_key": "inchi_key",
}

# JSON fields to serialize
_JSON_FIELDS: tuple[str, ...] = (
    "molecule_hierarchy",
    "molecule_properties",
    "molecule_structures",
    "molecule_synonyms",
    "cross_references",
    "atc_classifications",
)


# ============================================================================
# Declarative field groups for Molecule entity
# ============================================================================

_CORE_METADATA = FieldGroup(
    name="core_metadata",
    fields=(
        *simple_fields("pref_name", "molecule_type", "structure_type"),
        *int_fields("max_phase", "first_approval"),
    ),
)

_MOLECULE_FLAGS = FieldGroup(
    name="molecule_flags",
    fields=(
        *simple_fields(
            "oral", "parenteral", "topical", "therapeutic_flag", "withdrawn_flag"
        ),
        *int_fields(
            "black_box_warning",
            "natural_product",
            "first_in_class",
            "prodrug",
            "inorganic_flag",
            "polymer_flag",
            "chirality",
            "dosed_ingredient",
            "availability_type",
        ),
    ),
)

_ADDITIONAL_METADATA = FieldGroup(
    name="additional_metadata",
    fields=(
        *simple_fields(
            "usan_stem",
            "usan_stem_definition",
            "usan_substem",
            "helm_notation",
            "molecule_species",
        ),
        *int_fields("usan_year"),
    ),
)

# All declarative field groups
_MOLECULE_GROUPS: tuple[FieldGroup, ...] = (
    _CORE_METADATA,
    _MOLECULE_FLAGS,
    _ADDITIONAL_METADATA,
)


class MoleculeTransformer(BaseChemblTransformer):
    """Transforms ChEMBL bronze molecule records to silver."""

    entity_class = Molecule
    primary_id_field = "molecule_chembl_id"

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
        # Cast to dict for type-safe access to .get() method
        rec = cast("dict[str, Any]", record)

        # Extract structure fields
        structure_data = flatten_nested_dict(
            cast("dict[str, Any] | None", rec.get("molecule_structures")),
            "",  # No prefix - unified naming with PubChem
            _STRUCTURES_FIELDS,
            renames=_STRUCTURES_RENAMES,
        )

        # Validate InChI Key using Value Object (returns None for invalid/empty)
        inchi_key = InChIKey.from_raw(structure_data.get("inchi_key"))
        structure_data["inchi_key"] = str(inchi_key) if inchi_key else None

        # Validate SMILES using Value Object (returns None for invalid/empty)
        # ChEMBL provides canonical_smiles, so mark as canonical
        smiles = SMILES.from_raw(
            structure_data.get("canonical_smiles"),
            is_canonical=True,
        )
        structure_data["canonical_smiles"] = str(smiles) if smiles else None

        return {
            # Primary identifier
            "molecule_chembl_id": str(primary_id),
            # Declarative field groups (uses BronzeRecord type)
            **map_field_groups(record, _MOLECULE_GROUPS),
            # JSON serialization using helper method
            **self.serialize_json_fields(rec, _JSON_FIELDS),
            # Nested dict extraction with renames
            **flatten_nested_dict(
                cast("dict[str, Any] | None", rec.get("molecule_hierarchy")),
                "hierarchy_",
                _HIERARCHY_FIELDS,
                renames=_HIERARCHY_RENAMES,
            ),
            **flatten_nested_dict(
                cast("dict[str, Any] | None", rec.get("molecule_properties")),
                "property_",
                _PROPERTIES_FIELDS,
                renames=_PROPERTIES_RENAMES,
            ),
            # Structure data with validated InChI Key and SMILES
            **structure_data,
        }
