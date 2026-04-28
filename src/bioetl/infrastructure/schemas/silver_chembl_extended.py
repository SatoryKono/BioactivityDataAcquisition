"""ChEMBL Silver schemas (extended entities)."""

from __future__ import annotations

import pyarrow as pa

from bioetl.infrastructure.schemas.silver_common_field_blocks import (
    build_silver_dq_suffix_fields,
    build_silver_system_prefix_fields,
)

CHEMBL_DOCUMENT_TERM_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        *build_silver_system_prefix_fields(entity_id_nullable=False),
        # === Business fields (alphabetical order) ===
        pa.field("publication_id", pa.string()),
        pa.field("mesh_id", pa.string()),
        pa.field("qualifier", pa.string()),
        pa.field("term", pa.string()),
        pa.field("term_type", pa.string()),
        # === DQ_FIELDS_SUFFIX ===
        *build_silver_dq_suffix_fields(),
    ]
)

# Schema for ChEMBL Molecule
# See: https://www.ebi.ac.uk/chembl/api/data/molecule
CHEMBL_MOLECULE_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.9.4) ===
        *build_silver_system_prefix_fields(),
        # === Business fields (alphabetical order) ===
        pa.field("atc_classifications", pa.string()),
        pa.field("availability_type", pa.float64()),  # Float for nullable int
        pa.field("black_box_warning", pa.int64()),
        pa.field("canonical_smiles", pa.string()),
        pa.field("chirality", pa.int64()),
        pa.field("cross_references", pa.string()),
        pa.field("dosed_ingredient", pa.int64()),
        pa.field("first_approval", pa.float64()),  # Float for nullable int
        pa.field("first_in_class", pa.int64()),
        pa.field("helm_notation", pa.string()),
        pa.field("hierarchy_active_chembl_id", pa.string()),
        pa.field("hierarchy_child_chembl_id", pa.string()),
        pa.field("hierarchy_parent_chembl_id", pa.string()),
        pa.field("inchi_key", pa.string()),
        pa.field("inorganic_flag", pa.int64()),
        pa.field("max_phase", pa.float64()),
        pa.field("molecule_id", pa.string(), nullable=False),
        pa.field("molecule_hierarchy", pa.string()),
        pa.field("molecule_properties", pa.string()),
        pa.field("molecule_species", pa.string()),
        pa.field("molecule_structures", pa.string()),
        pa.field("molecule_synonyms", pa.string()),
        pa.field("molecule_type", pa.string()),
        pa.field("natural_product", pa.int64()),
        pa.field("oral", pa.bool_()),
        pa.field("parenteral", pa.bool_()),
        pa.field("polymer_flag", pa.int64()),
        pa.field("pref_name", pa.string()),
        pa.field("prodrug", pa.int64()),
        pa.field("aromatic_ring_count", pa.int64()),
        pa.field("hba_count", pa.int64()),
        pa.field("hbd_count", pa.int64()),
        pa.field("heavy_atom_count", pa.int64()),
        pa.field("logp", pa.float64()),
        pa.field("logp_method", pa.string()),
        pa.field("molecular_formula", pa.string()),
        pa.field("molecular_weight", pa.float64()),
        pa.field("mw_freebase", pa.float64()),
        pa.field("polar_surface_area", pa.float64()),
        pa.field("qed_score", pa.float64()),
        pa.field("ro3_pass", pa.string()),
        pa.field("ro5_violation_count", pa.int64()),
        pa.field("rotatable_bond_count", pa.int64()),
        pa.field("standard_inchi", pa.string()),
        pa.field("structure_type", pa.string()),
        pa.field("therapeutic_flag", pa.bool_()),
        pa.field("topical", pa.bool_()),
        pa.field("usan_stem", pa.string()),
        pa.field("usan_stem_definition", pa.string()),
        pa.field("usan_substem", pa.string()),
        pa.field("usan_year", pa.float64()),  # Float for nullable int
        pa.field("withdrawn_flag", pa.bool_()),
        # === DQ_FIELDS_SUFFIX ===
        *build_silver_dq_suffix_fields(),
    ]
)

# Schema for ChEMBL Compound Record
# See: https://www.ebi.ac.uk/chembl/api/data/compound_record
CHEMBL_COMPOUND_RECORD_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        *build_silver_system_prefix_fields(),
        # === Business fields (alphabetical order) ===
        pa.field("compound_key", pa.string()),
        pa.field("compound_name", pa.string()),
        pa.field("publication_id", pa.string()),
        pa.field("molecule_id", pa.string()),
        pa.field("record_id", pa.int64(), nullable=False),
        pa.field("src_compound_id", pa.string()),
        pa.field("src_id", pa.int64()),
        # === DQ_FIELDS_SUFFIX ===
        *build_silver_dq_suffix_fields(),
    ]
)

# Schema for ChEMBL Document Similarity
# See: https://www.ebi.ac.uk/chembl/api/data/document_similarity
CHEMBL_DOCUMENT_SIMILARITY_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        *build_silver_system_prefix_fields(),
        # === Business fields (alphabetical order) ===
        # Derived metrics
        pa.field("avg_tani", pa.float64()),
        # Foreign keys
        pa.field("doc_1", pa.int64()),
        pa.field("doc_2", pa.int64()),
        pa.field("max_tani", pa.float64()),
        # Tanimoto coefficients
        pa.field("mol_tani", pa.float64()),
        # PubMed identifiers (numeric strings for cross-provider consistency)
        pa.field("pubmed_id1", pa.string()),
        pa.field("pubmed_id2", pa.string()),
        pa.field("sim_id", pa.int64(), nullable=False),
        pa.field("tid_tani", pa.float64()),
        # === DQ_FIELDS_SUFFIX ===
        *build_silver_dq_suffix_fields(),
    ]
)

# Schema for Semantic Scholar Publication
# See: https://api.semanticscholar.org/api-docs/graph

CHEMBL_PROTEIN_CLASS_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        *build_silver_system_prefix_fields(),
        # === Business fields (alphabetical order) ===
        # Hierarchy
        pa.field("class_level", pa.int64()),
        # Classification data
        pa.field("definition", pa.string()),
        # Additional metadata
        pa.field("downgraded", pa.int64()),
        pa.field("parent_id", pa.int64()),
        pa.field("pref_name", pa.string()),
        pa.field("protein_class_desc", pa.string()),
        pa.field("protein_class_id", pa.int64(), nullable=False),
        pa.field("replaced_by", pa.int64()),
        pa.field("short_name", pa.string()),
        pa.field("sort_order", pa.int64()),
        # === DQ_FIELDS_SUFFIX ===
        *build_silver_dq_suffix_fields(),
    ]
)

# Schema for ChEMBL AssayParameters
# See: https://www.ebi.ac.uk/chembl/api/data/assay_parameters
CHEMBL_ASSAY_PARAMETERS_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        *build_silver_system_prefix_fields(),
        # === Business fields (alphabetical order) ===
        # Foreign key
        pa.field("assay_id", pa.string()),
        # Primary identifier (surrogate)
        pa.field("assay_param_id", pa.int64(), nullable=False),
        pa.field("comments", pa.string()),
        # Raw values
        pa.field("relation", pa.string()),
        # Standardized values
        pa.field("standard_relation", pa.string()),
        pa.field("standard_text_value", pa.string()),
        pa.field("standard_type", pa.string()),
        pa.field("standard_units", pa.string()),
        pa.field("standard_value", pa.float64()),
        pa.field("text_value", pa.string()),
        # Parameter type
        pa.field("type_raw", pa.string()),
        pa.field("type", pa.string()),
        pa.field("units", pa.string()),
        pa.field("value", pa.float64()),
        # === DQ_FIELDS_SUFFIX ===
        *build_silver_dq_suffix_fields(),
    ]
)

__all__ = [
    "CHEMBL_ASSAY_PARAMETERS_SCHEMA",
    "CHEMBL_COMPOUND_RECORD_SCHEMA",
    "CHEMBL_DOCUMENT_SIMILARITY_SCHEMA",
    "CHEMBL_DOCUMENT_TERM_SCHEMA",
    "CHEMBL_MOLECULE_SCHEMA",
    "CHEMBL_PROTEIN_CLASS_SCHEMA",
]
