"""ChEMBL Silver layer schemas."""

from __future__ import annotations

import pyarrow as pa

CHEMBL_PUBLICATION_SCHEMA = pa.schema(
    [
        # === SYSTEM_FIELDS_PREFIX ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_source", pa.string()),  # Data source identifier: "chembl"
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # === LOOKUP_FIELDS_PREFIX ===
        pa.field("_lookup_method", pa.string()),
        pa.field("_original_id", pa.string()),
        # === PUBLICATION_METADATA_FIELDS ===
        # affiliations excluded per user request
        pa.field("authors", pa.string()),  # JSON array of author names
        pa.field("title", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("publication_year", pa.int64()),
        pa.field("volume", pa.string()),
        pa.field("issue", pa.string()),
        pa.field("page_first", pa.string()),  # Unified: from first_page
        pa.field("page_last", pa.string()),  # Unified: from last_page
        # === PUBLICATION_CROSSREF_FIELDS ===
        pa.field(
            "publication_id", pa.string(), nullable=False
        ),  # Primary key (provider)
        pa.field("publication_doi", pa.string()),  # Cross-reference: DOI
        pa.field("publication_pmid", pa.string()),  # Cross-reference: PubMed ID
        pa.field("publication_pmc_id", pa.string()),  # Cross-reference: PMC ID
        pa.field("doi", pa.string()),
        pa.field("pmc_id", pa.string()),  # Not available from ChEMBL API (None values)
        pa.field("pmid", pa.string()),
        # === Other fields (alphabetical) ===
        pa.field("abstract", pa.string()),
        pa.field("affiliation_list", pa.string()),  # JSON array (None for ChEMBL)
        pa.field("author_keys", pa.string()),  # Pipe-delimited Surname_F keys
        pa.field("author_orcids", pa.string()),
        pa.field("publication_type", pa.string()),  # Unified: from doc_type
        pa.field(
            "publication_type_unified", pa.string()
        ),  # Level 3: "Journal Article", etc.
        pa.field(
            "publication_subclass", pa.string()
        ),  # Level 2: "Original Experimental Data", etc.
        pa.field("publication_class", pa.string()),  # Level 1: "EXP" | "REV" | "PEER"
        pa.field(
            "publication_date", pa.string()
        ),  # Not available from ChEMBL API (None values)
        pa.field(
            "language", pa.string()
        ),  # Not available from ChEMBL API (None values)
        pa.field("is_oa", pa.bool_()),  # Not available from ChEMBL API (None values)
        pa.field("src_id", pa.int64()),
        # === Unified citation metrics ===
        pa.field("citations_received", pa.int64()),  # Unified: from citation_count
        pa.field(
            "citations_made", pa.int64()
        ),  # Unified: references made (N/A for ChEMBL)
        # === ChEMBL Release Metadata ===
        pa.field("chembl_release", pa.string()),  # e.g., CHEMBL_1, CHEMBL_34
        pa.field("creation_date", pa.string()),  # Record creation date (YYYY-MM-DD)
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# ---------------------------------------------------------
# Schema for ChEMBL Activity (all fields from ChEMBL API)
# See: https://www.ebi.ac.uk/chembl/api/data/activity
CHEMBL_ACTIVITY_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # === Business fields (alphabetical order) ===
        pa.field("action_type", pa.string()),
        pa.field("action_type_description", pa.string()),
        pa.field("action_type_parent_type", pa.string()),
        pa.field("activity_comment", pa.string()),
        pa.field("activity_id", pa.string(), nullable=False),
        pa.field("activity_properties", pa.string()),  # JSON string
        pa.field("assay_id", pa.string()),
        pa.field("assay_description", pa.string()),
        pa.field("assay_type", pa.string()),
        pa.field("assay_variant_accession", pa.string()),
        pa.field("assay_variant_mutation", pa.string()),
        pa.field("bao_endpoint", pa.string()),
        pa.field("bao_format", pa.string()),
        pa.field("bao_label", pa.string()),
        pa.field("canonical_smiles", pa.string()),
        pa.field("data_validity_comment", pa.string()),
        pa.field("data_validity_description", pa.string()),
        pa.field("publication_id", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("publication_doi", pa.string()),  # Cross-reference: DOI
        pa.field("publication_pmid", pa.string()),  # Cross-reference: PubMed ID
        pa.field("publication_pmc_id", pa.string()),  # Cross-reference: PMC ID
        pa.field("publication_year", pa.int64()),
        pa.field("ligand_efficiency_bei", pa.float64()),
        pa.field("ligand_efficiency_le", pa.float64()),
        pa.field("ligand_efficiency_lle", pa.float64()),
        pa.field("ligand_efficiency_sei", pa.float64()),
        pa.field("manual_curation_flag", pa.float64()),  # Float for nullable int
        pa.field("molecule_id", pa.string()),
        pa.field("molecule_pref_name", pa.string()),
        pa.field("original_activity_id", pa.float64()),  # Float for nullable int
        pa.field("parent_molecule_id", pa.string()),
        pa.field("pchembl_value", pa.float64()),
        pa.field("potential_duplicate", pa.int64()),
        pa.field("qudt_units", pa.string()),
        pa.field("record_id", pa.int64()),
        pa.field("relation", pa.string()),
        pa.field("src_id", pa.int64()),
        pa.field("standard_flag", pa.int64()),
        pa.field("standard_relation", pa.string()),
        pa.field("standard_text_value", pa.string()),
        pa.field("standard_type", pa.string()),
        pa.field("standard_units", pa.string()),
        pa.field("standard_upper_value", pa.float64()),
        pa.field("standard_value", pa.float64()),
        pa.field("target_id", pa.string()),
        pa.field("target_organism", pa.string()),
        pa.field("target_pref_name", pa.string()),
        pa.field("target_taxonomy_id", pa.float64()),
        pa.field("text_value", pa.string()),
        pa.field("toid", pa.float64()),  # Float for nullable int (Pandas convention)
        pa.field("type", pa.string()),
        pa.field("units", pa.string()),
        pa.field("uo_units", pa.string()),
        pa.field("upper_value", pa.float64()),
        pa.field("value", pa.float64()),
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# Schema for PubChem Compound
# Aligned with domain/entities/pubchem.py (PubchemMolecule domain entity)
# and application/pipelines/pubchem/transformer.py (PubChemCompoundTransformer)

CHEMBL_ASSAY_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # === Business fields (alphabetical order) ===
        pa.field("aidx", pa.string()),
        pa.field("assay_category", pa.string()),
        pa.field("assay_cell_type", pa.string()),
        pa.field("assay_id", pa.string(), nullable=False),
        pa.field("assay_classifications", pa.string()),  # JSON string
        pa.field("assay_group", pa.string()),
        pa.field("assay_organism", pa.string()),
        pa.field("assay_parameters", pa.string()),  # JSON string
        pa.field("assay_pref_name", pa.string()),
        pa.field("assay_strain", pa.string()),
        pa.field("assay_subcellular_fraction", pa.string()),
        pa.field("assay_taxonomy_id", pa.float64()),
        pa.field("assay_test_type", pa.string()),
        pa.field("assay_tissue", pa.string()),
        pa.field("assay_type", pa.string()),
        pa.field("assay_type_description", pa.string()),
        pa.field("bao_format", pa.string()),
        pa.field("bao_label", pa.string()),
        pa.field("cell_id", pa.string()),
        pa.field("confidence_description", pa.string()),
        pa.field("confidence_score", pa.int64()),
        pa.field("description", pa.string()),
        pa.field("publication_id", pa.string()),
        pa.field("relationship_description", pa.string()),
        pa.field("relationship_type", pa.string()),
        pa.field("score", pa.float64()),
        pa.field("src_assay_id", pa.string()),
        pa.field("src_id", pa.int64()),
        pa.field("target_id", pa.string()),
        pa.field("tissue_id", pa.string()),
        # Variant information (flattened from ChEMBL API nested structure)
        pa.field("variant_accession", pa.string()),
        pa.field("variant_isoform", pa.string()),
        pa.field("variant_mutation", pa.string()),
        pa.field("variant_organism", pa.string()),
        pa.field("variant_sequence", pa.string()),
        pa.field("variant_sequence_json", pa.string()),  # Forensic: original JSON
        pa.field("variant_taxonomy_id", pa.float64()),
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# Schema for ChEMBL Target
# See: https://www.ebi.ac.uk/chembl/api/data/target
CHEMBL_TARGET_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # === Business fields (alphabetical order) ===
        pa.field("component_accessions", pa.string()),
        pa.field("component_descriptions", pa.string()),
        pa.field("component_ids", pa.string()),
        pa.field("component_relationships", pa.string()),
        pa.field("component_types", pa.string()),
        pa.field("cross_references", pa.string()),
        pa.field("description", pa.string()),
        pa.field("downgraded", pa.bool_()),
        pa.field("organism", pa.string()),
        pa.field("organism_class", pa.string()),
        pa.field("pipeline_stages", pa.string()),
        pa.field("pref_name", pa.string()),
        pa.field("primary_component_id", pa.float64()),
        pa.field("species_group_flag", pa.bool_()),
        pa.field("target_component_synonyms", pa.string()),
        pa.field("target_components", pa.string()),
        pa.field("target_id", pa.string(), nullable=False),
        pa.field("target_type", pa.string()),
        pa.field("taxonomy_id", pa.float64()),
        # Note: protein_classifications not available in /target endpoint
        # Use /target_component endpoint instead (CHEMBL_TARGET_COMPONENT_SCHEMA)
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# Schema for ChEMBL Target Component
# See: https://www.ebi.ac.uk/chembl/api/data/target_component
CHEMBL_TARGET_COMPONENT_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # === Business fields (alphabetical order) ===
        pa.field("accession", pa.string()),
        pa.field("component_id", pa.int64(), nullable=False),
        pa.field("component_type", pa.string()),
        pa.field("description", pa.string()),
        pa.field("organism", pa.string()),
        pa.field("protein_classification_id", pa.int64()),
        pa.field("protein_classification_ids", pa.string()),
        pa.field("protein_classifications", pa.string()),  # Forensic JSON
        pa.field("target_component_synonyms", pa.string()),
        pa.field("target_component_xrefs", pa.string()),
        pa.field("taxonomy_id", pa.int64()),  # Standardized name (was tax_id)
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# Schema for ChEMBL Cell Line
# See: https://www.ebi.ac.uk/chembl/api/data/cell_line
CHEMBL_CELL_LINE_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # === Business fields (alphabetical order) ===
        pa.field("cell_id", pa.string(), nullable=False),
        pa.field("cell_description", pa.string()),
        pa.field("cell_name", pa.string()),
        pa.field("cell_source_organism", pa.string()),
        pa.field(
            "cell_source_taxonomy_id", pa.int64()
        ),  # Standardized name (was cell_source_tax_id)
        pa.field("cell_source_tissue", pa.string()),
        # External identifiers
        pa.field("cellosaurus_id", pa.string()),
        pa.field("cl_lincs_id", pa.string()),
        pa.field("efo_id", pa.string()),
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# Schema for ChEMBL Tissue
# See: https://www.ebi.ac.uk/chembl/api/data/tissue
CHEMBL_TISSUE_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # === Business fields (alphabetical order) ===
        pa.field("bto_id", pa.string()),  # BRENDA Tissue Ontology
        pa.field("caloha_id", pa.string()),  # CALIPHO ID
        pa.field("efo_id", pa.string()),  # Experimental Factor Ontology
        pa.field("pref_name", pa.string()),  # Preferred tissue name
        pa.field("tissue_id", pa.string(), nullable=False),  # Primary key
        pa.field("uberon_id", pa.string()),  # Uberon Ontology
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)
# Derived entity extracted from Assay records (assay_subcellular_fraction field)
# Lookup table for subcellular fractions used in bioassays
CHEMBL_SUBCELLULAR_FRACTION_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string(), nullable=False),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # === Business fields (alphabetical order) ===
        pa.field("assay_count", pa.int64()),  # Number of assays using this fraction
        pa.field("example_assay_id", pa.string()),  # Example assay ChEMBL ID
        pa.field("subcellular_fraction", pa.string()),  # Primary key - fraction name
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# Derived entity extracted from Document records
# See: https://www.ebi.ac.uk/chembl/api/data/document
CHEMBL_DOCUMENT_TERM_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string(), nullable=False),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # === Business fields (alphabetical order) ===
        pa.field("publication_id", pa.string()),
        pa.field("mesh_id", pa.string()),
        pa.field("qualifier", pa.string()),
        pa.field("term", pa.string()),
        pa.field("term_type", pa.string()),
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# Schema for ChEMBL Molecule
# See: https://www.ebi.ac.uk/chembl/api/data/molecule
CHEMBL_MOLECULE_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.9.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
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
        pa.field("max_phase", pa.int64()),
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
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# Schema for ChEMBL Compound Record
# See: https://www.ebi.ac.uk/chembl/api/data/compound_record
CHEMBL_COMPOUND_RECORD_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # === Business fields (alphabetical order) ===
        pa.field("compound_key", pa.string()),
        pa.field("compound_name", pa.string()),
        pa.field("publication_id", pa.string()),
        pa.field("molecule_id", pa.string()),
        pa.field("record_id", pa.int64(), nullable=False),
        pa.field("src_compound_id", pa.string()),
        pa.field("src_id", pa.int64()),
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# Schema for ChEMBL Document Similarity
# See: https://www.ebi.ac.uk/chembl/api/data/document_similarity
CHEMBL_DOCUMENT_SIMILARITY_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
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
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# Schema for Semantic Scholar Publication
# See: https://api.semanticscholar.org/api-docs/graph

CHEMBL_PROTEIN_CLASS_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
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
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# Schema for ChEMBL AssayParameters
# See: https://www.ebi.ac.uk/chembl/api/data/assay_parameters
CHEMBL_ASSAY_PARAMETERS_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
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
        pa.field("type", pa.string()),
        pa.field("units", pa.string()),
        pa.field("value", pa.float64()),
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)
