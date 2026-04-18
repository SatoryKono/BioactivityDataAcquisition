"""ChEMBL Molecule Transformer.

Transforms Bronze records to Silver format (Molecule entity inflation).
Uses declarative field_specs DSL for mapping where applicable.
"""

from __future__ import annotations

__all__ = ["MoleculeTransformer"]


from typing import TYPE_CHECKING, cast

from bioetl.application.core.dict_transformers import flatten_nested_dict
from bioetl.application.core.field_specs import (
    FieldGroup,
    int_fields,
    map_field_groups,
    simple_fields,
)
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.domain.entities import Molecule
from bioetl.domain.transformations import safe_float, safe_int
from bioetl.domain.types import GoldRecord, JsonDict
from bioetl.domain.value_objects import SMILES, InChIKey

if TYPE_CHECKING:
    from bioetl.domain.types import BronzeRecord, PrimaryId

OptionalJsonDict = JsonDict | None


# Field mappings for molecule nested structures
_HIERARCHY_FIELDS: JsonDict = {  # Any: converter callables or None
    "parent_chembl_id": None,
    "active_chembl_id": None,
    "molecule_chembl_id": None,
    "molecule_id": None,
}

# Rename mapping for hierarchy fields (molecule_chembl_id -> child_chembl_id)
_HIERARCHY_RENAMES: dict[str, str] = {
    "hierarchy_molecule_chembl_id": "hierarchy_child_chembl_id",
    "hierarchy_molecule_id": "hierarchy_child_chembl_id",
}

_PROPERTIES_FIELDS: JsonDict = {  # Any: converter callables or None
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

# Rename mapping: all property_* fields → canonical alias names for Gold unification
_PROPERTIES_RENAMES: dict[str, str] = {
    "property_alogp": "logp",
    "property_mw_freebase": "mw_freebase",
    "property_full_mwt": "molecular_weight",
    "property_hba": "hba_count",
    "property_hbd": "hbd_count",
    "property_psa": "polar_surface_area",
    "property_rtb": "rotatable_bond_count",
    "property_num_ro5_violations": "ro5_violation_count",
    "property_heavy_atoms": "heavy_atom_count",
    "property_aromatic_rings": "aromatic_ring_count",
    "property_qed_weighted": "qed_score",
    "property_full_molformula": "molecular_formula",
    "property_ro3_pass": "ro3_pass",
}

_STRUCTURES_FIELDS: JsonDict = {  # Any: converter callables or None
    "canonical_smiles": None,
    "standard_inchi": None,
    "standard_inchi_key": None,
}

# Rename mapping for structures fields (standard_inchi_key -> inchikey for IUPAC/PubChem consistency)
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
    primary_id_field = "molecule_id"

    def _prepare_record(
        self,
        record: BronzeRecord,
    ) -> BronzeRecord:
        """Support both unified and legacy molecule identifier field names."""
        if "molecule_id" not in record and record.get("molecule_chembl_id") is not None:
            record = dict(record)
            record["molecule_id"] = record.get("molecule_chembl_id")
        return record

    def _extract_business_data(
        self,
        record: BronzeRecord,
        primary_id: PrimaryId,
    ) -> GoldRecord:
        """Extract Molecule business data from bronze record.

        Args:
            record: Raw Bronze record from ChEMBL API.
            primary_id: Validated molecule_id value.

        Returns:
            Dictionary of Molecule business fields.

        """
        # BronzeRecord is already a JsonDict
        rec = record

        # Extract structure fields
        structure_data = flatten_nested_dict(
            cast(
                OptionalJsonDict,
                rec.get("molecule_structures"),
            ),
            "",  # No prefix - unified naming with PubChem
            _STRUCTURES_FIELDS,
            renames=_STRUCTURES_RENAMES,
        )

        # Validate InChI Key using Value Object (returns None for invalid/empty)
        structure_data["inchi_key"] = self.validate_value_object(
            InChIKey, structure_data.get("inchi_key")
        )

        # Validate SMILES using Value Object (returns None for invalid/empty)
        # ChEMBL provides canonical_smiles, so mark as canonical
        smiles = SMILES.from_raw(
            structure_data.get("canonical_smiles"),
            is_canonical=True,
        )
        structure_data["canonical_smiles"] = str(smiles) if smiles else None

        properties = flatten_nested_dict(
            cast(
                OptionalJsonDict,
                rec.get("molecule_properties"),
            ),
            "property_",
            _PROPERTIES_FIELDS,
            renames=_PROPERTIES_RENAMES,
        )
        # ChEMBL provides only ALogP (Wildman-Crippen method) via
        # molecule_properties.alogp; tag identifies calculation method
        # for Gold-layer cross-provider unification.
        if properties.get("logp") is not None:
            properties["logp_method"] = "alogp"

        return {
            # Primary identifier (canonical)
            "molecule_id": str(primary_id),
            # Declarative field groups (uses BronzeRecord type)
            **map_field_groups(record, _MOLECULE_GROUPS),
            # JSON serialization using helper method
            **self.serialize_json_fields(rec, _JSON_FIELDS),
            # Nested dict extraction with renames
            **flatten_nested_dict(
                cast(
                    OptionalJsonDict,
                    rec.get("molecule_hierarchy"),
                ),
                "hierarchy_",
                _HIERARCHY_FIELDS,
                renames=_HIERARCHY_RENAMES,
            ),
            **properties,
            # Structure data with validated InChI Key and SMILES
            **structure_data,
        }
