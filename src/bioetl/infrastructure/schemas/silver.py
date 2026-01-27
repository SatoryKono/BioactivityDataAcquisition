"""Silver layer schemas for Delta Lake tables.

Defines the PyArrow schemas for various entities in the Silver layer.

Column Order Convention (per RULES.md §2.4 and ADR-014):
1. System prefix fields (entity_id, content_hash, _run_id, _run_type,
   _source_batch_id, _ingestion_ts, _index) - MUST be first
2. Business fields - sorted alphabetically
3. DQ suffix fields (_dq_warn, _dq_error) - MUST be last (if present)
"""

from __future__ import annotations

import pyarrow as pa

# ---------------------------------------------------------
# Schema for ChEMBL Publication (formerly Document)
# See: https://www.ebi.ac.uk/chembl/api/data/document
# Column order: SYSTEM_FIELDS_PREFIX, LOOKUP_FIELDS_PREFIX,
#               PUBLICATION_METADATA_FIELDS, PUBLICATION_CROSSREF_FIELDS,
#               other fields (alphabetical), DQ_FIELDS_SUFFIX
# ---------------------------------------------------------
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
        pa.field("year", pa.int64()),
        pa.field("volume", pa.string()),
        pa.field("issue", pa.string()),
        pa.field("first_page", pa.string()),
        pa.field("last_page", pa.string()),
        # === PUBLICATION_CROSSREF_FIELDS ===
        pa.field("document_chembl_id", pa.string()),  # Primary key
        pa.field("doi", pa.string()),
        # pmc_id excluded: not available from ChEMBL API
        pa.field("pmid", pa.string()),  # PubMed ID (numeric string)
        # === Other fields (alphabetical) ===
        pa.field("abstract", pa.string()),
        pa.field("doc_type", pa.string()),  # PUBLICATION, PATENT, DATASET, BOOK
        pa.field("journal_full_title", pa.string()),
        # publication_date excluded: not available from ChEMBL API
        pa.field("src_id", pa.int64()),
        # === ChEMBL Release Metadata ===
        pa.field("chembl_release", pa.string()),  # e.g., CHEMBL_1, CHEMBL_34
        pa.field("creation_date", pa.string()),  # Record creation date (YYYY-MM-DD)
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
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
        pa.field("action_type_action_type", pa.string()),
        pa.field("action_type_description", pa.string()),
        pa.field("action_type_parent_type", pa.string()),
        pa.field("activity_comment", pa.string()),
        pa.field("activity_id", pa.string()),
        pa.field("activity_properties", pa.string()),  # JSON string
        pa.field("assay_chembl_id", pa.string()),
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
        pa.field("document_chembl_id", pa.string()),
        pa.field("document_journal", pa.string()),
        pa.field("document_year", pa.int64()),
        pa.field("ligand_efficiency_bei", pa.float64()),
        pa.field("ligand_efficiency_le", pa.float64()),
        pa.field("ligand_efficiency_lle", pa.float64()),
        pa.field("ligand_efficiency_sei", pa.float64()),
        pa.field("manual_curation_flag", pa.int64()),
        pa.field("molecule_chembl_id", pa.string()),
        pa.field("molecule_pref_name", pa.string()),
        pa.field("original_activity_id", pa.int64()),
        pa.field("parent_molecule_chembl_id", pa.string()),
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
        pa.field("target_chembl_id", pa.string()),
        pa.field("target_organism", pa.string()),
        pa.field("target_pref_name", pa.string()),
        pa.field(
            "target_taxonomy_id", pa.string()
        ),  # Standardized name (was target_tax_id)
        pa.field("text_value", pa.string()),
        pa.field("toid", pa.int64()),
        pa.field("type", pa.string()),
        pa.field("units", pa.string()),
        pa.field("uo_units", pa.string()),
        pa.field("upper_value", pa.float64()),
        pa.field("value", pa.float64()),
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
    ]
)

# Schema for PubChem Compound
# Aligned with domain/entities/pubchem.py (PubchemMolecule domain entity)
# and application/pipelines/pubchem/transformer.py (PubChemCompoundTransformer)
PUBCHEM_COMPOUND_SCHEMA = pa.schema(
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
        pa.field("canonical_smiles", pa.string()),
        pa.field("cid", pa.string()),  # Domain entity uses str for cid
        pa.field("inchi", pa.string()),
        pa.field("inchikey", pa.string()),  # Matches domain entity field name
        pa.field("isomeric_smiles", pa.string()),
        pa.field("iupac_name", pa.string()),
        pa.field("molecular_formula", pa.string()),
        pa.field(
            "molecular_weight", pa.float64()
        ),  # Transformed to float by transformer
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
    ]
)

# Schema for UniProt Protein
UNIPROT_PROTEIN_SCHEMA = pa.schema(
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
        pa.field("entry_name", pa.string()),
        pa.field("gene_names", pa.list_(pa.string())),
        pa.field("organism_id", pa.int64()),
        pa.field("protein_name", pa.string()),
        pa.field("sequence_length", pa.int64()),
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
    ]
)

# Schema for UniProt ID Mapping
# Maps ChEMBL target IDs to UniProt accessions
UNIPROT_ID_MAPPING_SCHEMA = pa.schema(
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
        # Mapping status: 'found', 'not_found', 'error'
        pa.field("mapping_status", pa.string()),
        # Primary key (source identifier)
        pa.field("target_chembl_id", pa.string()),
        # Mapped identifier (nullable - None if not found)
        pa.field("uniprot_accession", pa.string()),
        # === DQ suffix (MUST be last, if present) ===
        # DQ warning flag (True for not_found)
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
    ]
)

# Schema for PubMed Publication
# Matches Publication entity from domain/entities.py
# See: https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html
# See also: https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_230101.dtd
PUBMED_PUBLICATION_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_source", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # === Business fields (alphabetical order) ===
        # Lookup metadata
        pa.field("_lookup_method", pa.string()),
        pa.field("_original_id", pa.string()),
        # Title and abstract
        pa.field("abstract", pa.string()),
        pa.field(
            "abstract_structured", pa.bool_()
        ),  # Whether abstract has NLM sections
        # Dates (ISO format strings)
        pa.field("accepted_date", pa.string()),
        # Authors (affiliations excluded per user request)
        pa.field("author_count", pa.int64()),  # Denormalized count for query efficiency
        pa.field("authors", pa.string()),  # JSON-serialized list
        # Counts (denormalized for query efficiency)
        pa.field("chemical_count", pa.int64()),
        pa.field("citation_subset", pa.string()),  # Citation subset codes (e.g., 'AIM')
        # Additional metadata
        pa.field("country", pa.string()),
        # MEDLINE dates
        pa.field("date_completed", pa.string()),  # MEDLINE processing completion date
        pa.field("date_revised", pa.string()),  # Record revision date (MEDLINE)
        # Primary identifiers
        pa.field("doi", pa.string()),
        pa.field("epub_date", pa.string()),
        # Unified page fields (parsed from medline_pgn/pages)
        pa.field("first_page", pa.string()),
        pa.field("grant_count", pa.int64()),  # Number of grants
        # Journal information
        pa.field("issn", pa.string()),
        pa.field("issue", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("journal_abbrev", pa.string()),
        # PubMed-specific journal fields (forensic retention)
        pa.field("journal_iso_abbrev", pa.string()),  # ISO journal abbreviation
        pa.field(
            "journal_issn_type", pa.string()
        ),  # ISSN type: Print/Electronic/Linking
        pa.field("journal_title", pa.string()),  # Full journal name (PubMed source)
        pa.field("keyword_count", pa.int64()),  # Number of keywords
        # Classification
        pa.field("keywords", pa.list_(pa.string())),
        pa.field("language", pa.string()),
        pa.field("last_page", pa.string()),
        # Page numbers (MEDLINE format)
        pa.field("medline_pgn", pa.string()),  # Original PubMed pagination
        pa.field("mesh_heading_count", pa.int64()),  # Number of MeSH headings
        pa.field("mesh_terms", pa.list_(pa.string())),
        pa.field("nlm_unique_id", pa.string()),  # NLM catalog ID
        pa.field("pages", pa.string()),  # Legacy: medline_pgn format
        pa.field("pmc_id", pa.string()),
        pa.field("pmid", pa.string()),
        pa.field("pub_date", pa.string()),
        pa.field("pub_day", pa.int64()),  # Publication day (1-31)
        pa.field("pub_month", pa.int64()),  # Publication month (1-12)
        pa.field("publication_date", pa.string()),  # Unified: YYYY-MM-DD format
        pa.field("publication_status", pa.string()),  # ppublish/epublish/aheadofprint
        pa.field("publication_type_list", pa.string()),  # JSON array of pub types
        pa.field("publication_types", pa.list_(pa.string())),
        pa.field("publication_year", pa.int64()),  # Legacy alias for year
        pa.field("received_date", pa.string()),
        pa.field("reference_count", pa.int64()),  # Number of references
        pa.field("revised_date", pa.string()),
        pa.field("title", pa.string()),
        pa.field("vernacular_title", pa.string()),  # Original non-English title
        pa.field("volume", pa.string()),
        pa.field("year", pa.int64()),
        # === DQ suffix (MUST be last, per RULES.md §2.4) ===
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
    ]
)

# Schema for ChEMBL Assay
# See: https://www.ebi.ac.uk/chembl/api/data/assay
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
        pa.field("assay_chembl_id", pa.string()),
        pa.field("assay_classifications", pa.string()),  # JSON string
        pa.field("assay_group", pa.string()),
        pa.field("assay_organism", pa.string()),
        pa.field("assay_parameters", pa.string()),  # JSON string
        pa.field("assay_pref_name", pa.string()),
        pa.field("assay_strain", pa.string()),
        pa.field("assay_subcellular_fraction", pa.string()),
        pa.field(
            "assay_taxonomy_id", pa.int64()
        ),  # Standardized name (was assay_tax_id)
        pa.field("assay_test_type", pa.string()),
        pa.field("assay_tissue", pa.string()),
        pa.field("assay_type", pa.string()),
        pa.field("assay_type_description", pa.string()),
        pa.field("bao_format", pa.string()),
        pa.field("bao_label", pa.string()),
        pa.field("cell_chembl_id", pa.string()),
        pa.field("confidence_description", pa.string()),
        pa.field("confidence_score", pa.int64()),
        pa.field("description", pa.string()),
        pa.field("document_chembl_id", pa.string()),
        pa.field("relationship_description", pa.string()),
        pa.field("relationship_type", pa.string()),
        pa.field("score", pa.float64()),
        pa.field("src_assay_id", pa.string()),
        pa.field("src_id", pa.int64()),
        pa.field("target_chembl_id", pa.string()),
        pa.field("tissue_chembl_id", pa.string()),
        # Variant information (flattened from ChEMBL API nested structure)
        pa.field("variant_accession", pa.string()),
        pa.field("variant_isoform", pa.string()),
        pa.field("variant_mutation", pa.string()),
        pa.field("variant_organism", pa.string()),
        pa.field("variant_sequence", pa.string()),
        pa.field("variant_sequence_json", pa.string()),  # Forensic: original JSON
        pa.field(
            "variant_taxonomy_id", pa.int64()
        ),  # Standardized name (was variant_tax_id)
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
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
        # Flattened component fields
        pa.field("component_accessions", pa.list_(pa.string())),
        pa.field("component_descriptions", pa.list_(pa.string())),
        pa.field("component_ids", pa.list_(pa.int64())),
        pa.field("component_organisms", pa.list_(pa.string())),
        pa.field("component_relationships", pa.list_(pa.string())),
        pa.field(
            "component_taxonomy_ids", pa.list_(pa.int64())
        ),  # Standardized name (was component_tax_ids)
        pa.field("component_types", pa.list_(pa.string())),
        # Complex fields (JSON strings)
        pa.field("cross_references", pa.string()),
        pa.field("dap_id", pa.int64()),
        pa.field("description", pa.string()),
        pa.field("downgraded", pa.bool_()),
        pa.field("organism", pa.string()),
        pa.field("pipeline_stages", pa.string()),
        pa.field("pref_name", pa.string()),
        pa.field("species_group_flag", pa.bool_()),
        pa.field("target_chembl_id", pa.string()),
        pa.field("target_component_synonyms", pa.string()),
        pa.field("target_components", pa.string()),
        pa.field("target_constraints", pa.string()),
        pa.field("target_type", pa.string()),
        pa.field("taxonomy_id", pa.int64()),  # Standardized name (was tax_id)
        # Note: protein_classifications not available in /target endpoint
        # Use /target_component endpoint instead (CHEMBL_TARGET_COMPONENT_SCHEMA)
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
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
        pa.field("component_id", pa.int64()),
        pa.field("component_type", pa.string()),
        pa.field("description", pa.string()),
        pa.field("organism", pa.string()),
        # Flattened fields (extracted from protein_classifications)
        pa.field("protein_classification_ids", pa.list_(pa.int64())),
        pa.field("protein_classifications", pa.string()),  # Forensic JSON
        # Complex fields (JSON strings)
        pa.field("target_component_synonyms", pa.string()),
        pa.field("target_component_xrefs", pa.string()),
        pa.field("taxonomy_id", pa.int64()),  # Standardized name (was tax_id)
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
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
        pa.field("cell_chembl_id", pa.string()),
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
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
    ]
)

# Schema for ChEMBL Document Term
# Derived entity extracted from Document records
# See: https://www.ebi.ac.uk/chembl/api/data/document
CHEMBL_DOCUMENT_TERM_SCHEMA = pa.schema(
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
        pa.field("document_chembl_id", pa.string()),
        # MeSH-specific fields
        pa.field("mesh_id", pa.string()),
        pa.field("qualifier", pa.string()),
        pa.field("term", pa.string()),
        pa.field("term_type", pa.string()),
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
    ]
)

# Schema for ChEMBL Molecule
# See: https://www.ebi.ac.uk/chembl/api/data/molecule
CHEMBL_MOLECULE_SCHEMA = pa.schema(
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
        pa.field("atc_classifications", pa.string()),
        pa.field("availability_type", pa.int64()),
        pa.field("black_box_warning", pa.int64()),
        # Flattened Structures (unified naming without structure_ prefix)
        pa.field("canonical_smiles", pa.string()),
        pa.field("chirality", pa.int64()),
        # Complex fields (JSON strings)
        pa.field("cross_references", pa.string()),
        pa.field("dosed_ingredient", pa.int64()),
        pa.field("first_approval", pa.int64()),
        pa.field("first_in_class", pa.int64()),
        pa.field("helm_notation", pa.string()),
        # Flattened Hierarchy
        pa.field("hierarchy_active_chembl_id", pa.string()),
        pa.field("hierarchy_child_chembl_id", pa.string()),
        pa.field("hierarchy_parent_chembl_id", pa.string()),
        pa.field("inchi_key", pa.string()),
        pa.field("inorganic_flag", pa.int64()),
        pa.field("max_phase", pa.int64()),
        pa.field("molecule_chembl_id", pa.string()),
        pa.field("molecule_hierarchy", pa.string()),
        pa.field("molecule_properties", pa.string()),
        pa.field("molecule_species", pa.string()),
        pa.field("molecule_structures", pa.string()),
        pa.field("molecule_synonyms", pa.string()),
        pa.field("molecule_type", pa.string()),
        pa.field("natural_product", pa.int64()),
        # Flags
        pa.field("oral", pa.bool_()),
        pa.field("parenteral", pa.bool_()),
        pa.field("polymer_flag", pa.int64()),
        pa.field("pref_name", pa.string()),
        pa.field("prodrug", pa.int64()),
        # Flattened Properties
        pa.field("property_alogp", pa.float64()),
        pa.field("property_aromatic_rings", pa.int64()),
        pa.field("property_full_molformula", pa.string()),
        pa.field("property_full_mwt", pa.float64()),
        pa.field("property_hba", pa.int64()),
        pa.field("property_hbd", pa.int64()),
        pa.field("property_heavy_atoms", pa.int64()),
        pa.field("property_mw_freebase", pa.float64()),
        pa.field("property_psa", pa.float64()),
        pa.field("property_qed_weighted", pa.float64()),
        pa.field("property_ro3_pass", pa.string()),
        pa.field("property_ro5_violations", pa.int64()),
        pa.field("property_rtb", pa.int64()),
        pa.field("standard_inchi", pa.string()),
        pa.field("structure_type", pa.string()),
        pa.field("therapeutic_flag", pa.bool_()),
        pa.field("topical", pa.bool_()),
        # USAN naming
        pa.field("usan_stem", pa.string()),
        pa.field("usan_stem_definition", pa.string()),
        pa.field("usan_substem", pa.string()),
        pa.field("usan_year", pa.int64()),
        pa.field("withdrawn_flag", pa.bool_()),
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
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
        # Original compound names from the document
        pa.field("compound_key", pa.string()),
        pa.field("compound_name", pa.string()),
        # Foreign keys
        pa.field("document_chembl_id", pa.string()),
        pa.field("molecule_chembl_id", pa.string()),
        pa.field("record_id", pa.int64()),
        # Source information
        pa.field("src_compound_id", pa.string()),
        pa.field("src_id", pa.int64()),
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
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
        pa.field("sim_id", pa.int64()),
        pa.field("tid_tani", pa.float64()),
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
    ]
)

# Schema for Semantic Scholar Publication
# See: https://api.semanticscholar.org/api-docs/graph
SEMANTICSCHOLAR_PUBLICATION_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_source", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # === Business fields (alphabetical order) ===
        # Lookup metadata
        # _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
        # _original_id: Original identifier used for lookup
        pa.field("_lookup_method", pa.string()),
        pa.field("_original_id", pa.string()),
        # abstract, affiliations, authors excluded per user request
        # External IDs
        pa.field("arxiv_id", pa.string()),
        pa.field("author_ids", pa.string()),
        # Metrics
        pa.field("citation_count", pa.int64()),
        pa.field("corpus_id", pa.int64()),
        pa.field("doi", pa.string()),
        pa.field("fields_of_study", pa.string()),
        # Unified page fields (parsed from pages)
        pa.field("first_page", pa.string()),
        # Open Access
        pa.field("is_oa", pa.bool_()),
        # Journal/Venue
        pa.field("journal", pa.string()),
        pa.field("last_page", pa.string()),
        pa.field("oa_status", pa.string()),
        pa.field("open_access_url", pa.string()),
        pa.field("pages", pa.string()),  # Legacy: "first-last" format
        # Primary key
        pa.field("paper_id", pa.string()),
        # Cross-reference IDs for linking publications across providers
        # pmc_id: PubMed Central ID (format: "PMC1234567")
        pa.field("pmc_id", pa.string()),
        # pmid: PubMed ID (numeric string: "12345678")
        pa.field("pmid", pa.string()),
        pa.field("publication_date", pa.string()),
        pa.field("publication_types", pa.string()),
        pa.field("reference_count", pa.int64()),
        # Core fields
        pa.field("title", pa.string()),
        pa.field("tldr", pa.string()),
        pa.field("venue", pa.string()),
        pa.field("volume", pa.string()),
        pa.field("year", pa.int64()),
        # === DQ suffix (MUST be last, if present) ===
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
    ]
)

# Schema for CrossRef Publication
# See: https://api.crossref.org/swagger-ui/index.html
CROSSREF_PUBLICATION_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_source", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
        pa.field("_lookup_method", pa.string()),
        pa.field("_original_id", pa.string()),
        # === Business fields (alphabetical order) ===
        # abstract and affiliations excluded per user request
        pa.field("alternative_id", pa.list_(pa.string())),  # Publisher-specific IDs
        pa.field("authors", pa.string()),  # JSON-serialized list
        pa.field("citation_count", pa.int64()),
        pa.field("content_domain_crossmark_restriction", pa.bool_()),
        pa.field("content_domain_domains", pa.list_(pa.string())),
        pa.field("doc_type", pa.string()),
        # doi: Digital Object Identifier (lowercase, without "https://doi.org/") - Primary key
        pa.field("doi", pa.string()),
        pa.field("first_page", pa.string()),
        pa.field("issn", pa.list_(pa.string())),
        pa.field("issn_electronic", pa.string()),  # Electronic ISSN
        pa.field("issn_print", pa.string()),  # Print ISSN
        pa.field("issue", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("language", pa.string()),
        pa.field("last_page", pa.string()),
        pa.field("license_url", pa.string()),
        # Cross-reference IDs (nullable - CrossRef doesn't provide these natively)
        pa.field("pmc_id", pa.string()),  # PubMed Central ID
        pa.field("pmid", pa.string()),  # PubMed ID
        pa.field("publication_date", pa.string()),  # Unified: YYYY-MM-DD
        pa.field("published", pa.string()),  # Canonical publication date
        pa.field("published_online", pa.string()),  # Provider-specific
        pa.field("published_print", pa.string()),  # Provider-specific
        pa.field("publisher", pa.string()),
        pa.field("reference_count", pa.int64()),
        pa.field("short_container_title", pa.list_(pa.string())),
        pa.field("subjects", pa.list_(pa.string())),
        pa.field("title", pa.string()),
        pa.field("volume", pa.string()),
        pa.field("year", pa.int64()),
        # === DQ suffix (MUST be last, per RULES.md §2.4) ===
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
    ]
)

# Schema for OpenAlex Publication
# See: https://docs.openalex.org/api-entities/works
OPENALEX_PUBLICATION_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_source", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
        pa.field("_index", pa.int64()),
        # === Business fields (alphabetical order) ===
        # Lookup metadata
        # _lookup_method: "direct" | "doi" | "pmid" | "title_fallback" | "unknown"
        # _original_id: Original identifier used for lookup
        pa.field("_lookup_method", pa.string()),
        pa.field("_original_id", pa.string()),
        pa.field("abstract", pa.string()),
        pa.field("affiliations", pa.string()),
        pa.field("authors", pa.string()),  # JSON-serialized list
        # OpenAlex source field: cited_by_count
        # Unified BioETL field: citation_count (standardized across all providers)
        pa.field("citation_count", pa.int64()),
        pa.field("concepts", pa.list_(pa.string())),
        # Metadata
        pa.field("doc_type", pa.string()),
        # Cross-reference IDs for linking publications across providers
        # doi: Digital Object Identifier (lowercase, without "https://doi.org/")
        pa.field("doi", pa.string()),
        # Unified page fields (from biblio object)
        pa.field("first_page", pa.string()),
        # Field-Weighted Citation Impact (must be non-negative)
        pa.field("fwci", pa.float64()),
        # Institution identifiers (for cross-referencing and geographic analysis)
        pa.field("institution_country_codes", pa.list_(pa.string())),
        pa.field("institution_ids", pa.list_(pa.string())),
        pa.field("is_oa", pa.bool_()),
        # Quality indicators
        pa.field("is_retracted", pa.bool_()),
        # Journal info
        pa.field("issn", pa.string()),
        # Bibliographic info (from biblio object)
        pa.field("issue", pa.string()),
        pa.field("journal", pa.string()),
        # Keywords extracted from OpenAlex
        pa.field("keywords", pa.list_(pa.string())),
        pa.field("language", pa.string()),
        pa.field("last_page", pa.string()),
        # Microsoft Academic Graph ID (legacy, from ids object)
        pa.field("mag_id", pa.string()),
        # MeSH terms extracted from OpenAlex mesh field
        pa.field("mesh", pa.list_(pa.string())),
        pa.field("oa_status", pa.string()),
        # Primary key
        pa.field("openalex_id", pa.string()),
        # pmc_id: PubMed Central ID (format: "PMC1234567") - nullable, may not exist for all publications
        pa.field("pmc_id", pa.string()),
        # pmid: PubMed ID (numeric string: "12345678") - nullable, may not exist for all publications
        pa.field("pmid", pa.string()),
        # Date fields
        pa.field("publication_date", pa.string()),
        pa.field("publisher", pa.string()),
        # Number of works referenced (from referenced_works_count)
        pa.field("referenced_works_count", pa.int64()),
        pa.field("title", pa.string()),
        # Bibliographic info (from biblio object)
        pa.field("volume", pa.string()),
        pa.field("year", pa.int64()),
        # === DQ suffix (MUST be last, per RULES.md §2.4) ===
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
    ]
)

# Schema for ChEMBL Protein Classification
# See: https://www.ebi.ac.uk/chembl/api/data/protein_class
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
        pa.field("protein_class_id", pa.int64()),
        pa.field("replaced_by", pa.int64()),
        pa.field("short_name", pa.string()),
        pa.field("sort_order", pa.int64()),
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
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
        pa.field("assay_chembl_id", pa.string()),
        # Primary identifier (surrogate)
        pa.field("assay_param_id", pa.int64()),
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
        pa.field("_dq_warn", pa.bool_()),
        pa.field("_dq_error", pa.bool_()),
    ]
)
