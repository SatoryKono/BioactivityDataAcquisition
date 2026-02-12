"""Silver layer schemas for Delta Lake tables.

Defines the PyArrow schemas for various entities in the Silver layer.

Column Order Convention (per RULES.md §2.9.4 and ADR-014):
1. System prefix fields (entity_id, content_hash, _run_id, _run_type,
   _source_batch_id, _ingestion_ts, _index) - MUST be first
2. Business fields - sorted alphabetically
3. DQ suffix fields (_dq_error, _dq_warn) - MUST be last (if present)
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
        pa.field("publication_year", pa.int64()),
        pa.field("volume", pa.string()),
        pa.field("issue", pa.string()),
        pa.field("page_first", pa.string()),  # Unified: from first_page
        pa.field("page_last", pa.string()),  # Unified: from last_page
        # === PUBLICATION_CROSSREF_FIELDS ===
        pa.field("publication_id", pa.string()),  # Primary key (provider)
        pa.field("doi", pa.string()),
        pa.field("pmc_id", pa.string()),  # Not available from ChEMBL API (None values)
        pa.field("pmid", pa.string()),
        # === Other fields (alphabetical) ===
        pa.field("abstract", pa.string()),
        pa.field("affiliation_list", pa.string()),  # JSON array (None for ChEMBL)
        pa.field("author_ormolecule_ids", pa.string()),
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
        pa.field("action_type_action_type", pa.string()),
        pa.field("action_type_description", pa.string()),
        pa.field("action_type_parent_type", pa.string()),
        pa.field("activity_comment", pa.string()),
        pa.field("activity_id", pa.string()),
        pa.field("activity_properties", pa.string()),  # JSON string
        pa.field("assay_description", pa.string()),
        pa.field("assay_id", pa.string()),
        pa.field("assay_type", pa.string()),
        pa.field("assay_variant_accession", pa.string()),
        pa.field("assay_variant_mutation", pa.string()),
        pa.field("bao_endpoint", pa.string()),
        pa.field("bao_format", pa.string()),
        pa.field("bao_label", pa.string()),
        pa.field("canonical_smiles", pa.string()),
        pa.field("data_validity_comment", pa.string()),
        pa.field("data_validity_description", pa.string()),
        pa.field("document_journal", pa.string()),
        pa.field("document_year", pa.int64()),
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
        pa.field("publication_id", pa.string()),
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
        pa.field("taxonomy_id", pa.string()),
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
        pa.field("molecule_id", pa.string()),
        pa.field("complexity", pa.float64()),
        pa.field("conformer_count_3d", pa.float64()),
        pa.field("conformer_rmsd_3d", pa.float64()),
        pa.field("effective_rotor_count_3d", pa.float64()),
        pa.field("exact_mass", pa.float64()),
        pa.field("feature_acceptor_count_3d", pa.float64()),
        pa.field("feature_anion_count_3d", pa.float64()),
        pa.field("feature_cation_count_3d", pa.float64()),
        pa.field("feature_count_3d", pa.float64()),
        pa.field("feature_donor_count_3d", pa.float64()),
        pa.field("feature_hydrophobe_count_3d", pa.float64()),
        pa.field("feature_ring_count_3d", pa.float64()),
        pa.field("inchi", pa.string()),
        pa.field("inchi_key", pa.string()),
        pa.field("isomeric_smiles", pa.string()),
        pa.field("iupac_name", pa.string()),
        pa.field("molecular_formula", pa.string()),
        pa.field("molecular_weight", pa.float64()),
        pa.field("monoisotopic_mass", pa.float64()),
        pa.field("tpsa", pa.float64()),
        pa.field("x_steric_quadrupole_3d", pa.float64()),
        pa.field("xlogp", pa.float64()),
        pa.field("y_steric_quadrupole_3d", pa.float64()),
        pa.field("z_steric_quadrupole_3d", pa.float64()),
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# Schema for UniProt Protein
# Extended schema with functional annotations, cross-references, and quality metrics
# See: https://www.uniprot.org/help/return_fields
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
        pa.field("accession", pa.string()),  # Primary UniProt accession
        pa.field("acetylation", pa.string()),  # PTM: acetylation sites
        pa.field("active_sites", pa.string()),  # JSON: ft_act_site features
        pa.field("activity_regulation", pa.string()),  # cc_activity_regulation
        pa.field("annotation_score", pa.int64()),  # Quality score 1-5
        pa.field("binding_sites", pa.string()),  # JSON: ft_binding features
        pa.field("catalytic_activity", pa.string()),  # cc_catalytic_activity
        pa.field("cellular_component", pa.string()),  # GO aspect C
        pa.field("chembl_ids", pa.string()),  # ChEMBL target cross-refs (JSON array)
        pa.field("disease_involvement", pa.string()),  # cc_disease
        pa.field("disulfide_bond", pa.string()),  # PTM: disulfide bonds
        pa.field("domains", pa.string()),  # JSON: ft_domain features
        pa.field("drugbank_ids", pa.string()),  # DrugBank cross-refs (JSON array)
        pa.field("entry_name", pa.string()),  # UniProt entry name (e.g., FA10_HUMAN)
        pa.field("features_json", pa.string()),  # All features combined (forensic)
        pa.field("function_comment", pa.string()),  # cc_function
        pa.field("gene_names", pa.list_(pa.string())),  # Gene name synonyms
        pa.field("genus", pa.string()),  # Taxonomy: genus
        pa.field("glycosylation", pa.string()),  # PTM: glycosylation sites
        pa.field("go_terms", pa.string()),  # GO annotations (JSON array)
        pa.field("interpro_xrefs", pa.string()),  # InterPro domain IDs (JSON array)
        pa.field("intramembrane", pa.string()),  # Structural: intramembrane regions
        pa.field("isoform_ids", pa.string()),  # Isoform IDs (e.g., P12345-2)
        pa.field("isoform_names", pa.string()),  # Isoform names
        pa.field("isoform_synonyms", pa.string()),  # Isoform synonyms
        pa.field("lipidation", pa.string()),  # PTM: lipidation sites
        pa.field("modified_residue", pa.string()),  # PTM: all modified residues
        pa.field("molecular_function", pa.string()),  # GO aspect F
        pa.field("organism_id", pa.int64()),  # NCBI Taxonomy ID
        pa.field("pathway", pa.string()),  # cc_pathway
        pa.field("pdb_xrefs", pa.string()),  # PDB structure IDs (JSON array)
        pa.field("pfam_xrefs", pa.string()),  # Pfam family IDs (JSON array)
        pa.field("phosphorylation", pa.string()),  # PTM: phosphorylation sites
        pa.field("phylum", pa.string()),  # Taxonomy: phylum
        pa.field("propeptide", pa.string()),  # Structural: propeptide
        pa.field("protein_existence", pa.string()),  # Evidence level string
        pa.field("protein_name", pa.string()),  # Recommended protein name
        pa.field("reaction_ec_numbers", pa.string()),  # EC numbers from reactions
        pa.field("reactions", pa.string()),  # Reaction names from catalytic activity
        pa.field("reactome_xrefs", pa.string()),  # Reactome pathway IDs (JSON array)
        pa.field("reviewed", pa.bool_()),  # Swiss-Prot (true) vs TrEMBL (false)
        pa.field("sequence_length", pa.int64()),  # Protein sequence length
        pa.field("signal_peptide", pa.string()),  # Structural: signal peptide
        pa.field("similarity_comment", pa.string()),  # cc_similarity
        pa.field("subcellular_location", pa.string()),  # cc_subcellular_location
        pa.field("superkingdom", pa.string()),  # Taxonomy: superkingdom
        pa.field("tissue_specificity", pa.string()),  # cc_tissue_specificity
        pa.field("topology", pa.string()),  # Structural: topological domains
        pa.field("transmembrane", pa.string()),  # Structural: transmembrane regions
        pa.field("ubiquitination", pa.string()),  # PTM: ubiquitination sites
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)

# Schema for UniProt ID Mapping
# Maps ChEMBL target IDs to UniProt accessions with entry metadata
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
        pa.field("all_mappings", pa.string()),  # JSON array for multiple mappings
        pa.field("annotation_score", pa.int64()),  # Quality score 1-5
        pa.field("gene_primary", pa.string()),  # Primary gene name
        # Mapping status: 'found', 'not_found', 'error', 'multiple'
        pa.field("mapping_status", pa.string()),
        pa.field("organism_common", pa.string()),  # Common organism name
        pa.field("organism_scientific", pa.string()),  # Scientific organism name
        pa.field("protein_name", pa.string()),  # Recommended protein name
        pa.field("reviewed", pa.bool_()),  # Swiss-Prot (true) vs TrEMBL (false)
        pa.field("sequence_length", pa.int64()),  # Protein sequence length
        pa.field("sequence_mass", pa.int64()),  # Molecular weight in Daltons
        # Primary key (source identifier)
        pa.field("target_id", pa.string()),
        pa.field("taxonomy_id", pa.int64()),  # NCBI Taxonomy ID
        # Mapped identifier (nullable - None if not found)
        pa.field("uniprot_accession", pa.string()),
        pa.field("uniprot_entry_name", pa.string()),  # Entry name (e.g., FA10_HUMAN)
        # === DQ suffix (MUST be last, if present) ===
        # DQ warning flag (True for not_found)
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
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
        pa.field("_lookup_method", pa.string()),
        pa.field("_original_id", pa.string()),
        pa.field("abstract", pa.string()),
        pa.field(
            "abstract_structured", pa.bool_()
        ),  # Whether abstract has NLM sections
        pa.field("affiliation_list", pa.string()),  # JSON array of unique affiliations
        pa.field("affiliation_structured", pa.string()),  # JSON array with ROR/GRID
        pa.field("author_count", pa.int64()),
        pa.field("authors", pa.string()),  # JSON-serialized list
        pa.field("authors_with_affiliations", pa.string()),  # JSON array
        pa.field("chemical_count", pa.int64()),
        pa.field("chemicals", pa.string()),  # Chemical substances (JSON array)
        pa.field("citation_subset", pa.string()),  # Citation subset codes
        pa.field("citations_made", pa.int64()),  # Unified: citations made
        # citations_received: excluded (PubMed doesn't provide citation metrics)
        pa.field("country", pa.string()),
        pa.field("databanks", pa.string()),  # Databank accession numbers (JSON array)
        pa.field("date_completed", pa.string()),  # MEDLINE processing completion date
        pa.field("date_revised", pa.string()),  # Record revision date
        pa.field("doi", pa.string()),
        pa.field("gene_symbols", pa.string()),  # Gene symbols (JSON array)
        pa.field("grant_count", pa.int64()),
        # is_oa: excluded (PubMed doesn't provide OA status directly)
        pa.field("issn", pa.string()),
        pa.field("issue", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("journal_iso_abbrev", pa.string()),  # ISO journal abbreviation
        pa.field("journal_issn_type", pa.string()),  # Print/Electronic/Linking
        pa.field("journal_name_short", pa.string()),  # Journal abbreviation
        pa.field("keyword_count", pa.int64()),
        pa.field("language", pa.string()),
        pa.field("medline_pgn", pa.string()),  # Original PubMed pagination
        pa.field("mesh_heading_count", pa.int64()),
        pa.field("nlm_unique_id", pa.string()),  # NLM catalog ID
        pa.field("page_first", pa.string()),
        pa.field("page_last", pa.string()),
        pa.field("page_range", pa.string()),  # Page range string
        pa.field("pmc_id", pa.string()),
        pa.field("pmid", pa.string()),
        pa.field("pub_date", pa.string()),
        pa.field("pub_day", pa.int64()),  # Publication day (1-31)
        pa.field("pub_month", pa.int64()),  # Publication month (1-12)
        pa.field("publication_class", pa.string()),  # Level 1: "EXP" | "REV" | "PEER"
        pa.field("publication_date", pa.string()),  # Unified: YYYY-MM-DD format
        pa.field("publication_status", pa.string()),  # ppublish/epublish/aheadofprint
        pa.field(
            "publication_subclass", pa.string()
        ),  # Level 2: "Original Experimental Data", etc.
        pa.field("publication_type", pa.string()),  # Unified: publication type
        pa.field("publication_type_list", pa.string()),  # JSON array of pub types
        pa.field(
            "publication_type_unified", pa.string()
        ),  # Level 3: "Journal Article", etc.
        pa.field("publication_types", pa.list_(pa.string())),
        pa.field("publication_year", pa.int64()),
        pa.field("subject_keywords", pa.list_(pa.string())),  # Author keywords
        pa.field("subject_mesh", pa.list_(pa.string())),  # MeSH terms
        pa.field("title", pa.string()),
        pa.field("volume", pa.string()),
        # === DQ suffix (MUST be last, per RULES.md §2.4) ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
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
        pa.field("assay_classifications", pa.string()),  # JSON string
        pa.field("assay_group", pa.string()),
        pa.field("assay_id", pa.string()),
        pa.field("assay_organism", pa.string()),
        pa.field("assay_parameters", pa.string()),  # JSON string
        pa.field("assay_pref_name", pa.string()),
        pa.field("assay_strain", pa.string()),
        pa.field("assay_subcellular_fraction", pa.string()),
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
        pa.field("taxonomy_id", pa.string()),
        pa.field("tissue_id", pa.string()),
        # Variant information (flattened from ChEMBL API nested structure)
        pa.field("variant_accession", pa.string()),
        pa.field("variant_isoform", pa.string()),
        pa.field("variant_mutation", pa.string()),
        pa.field("variant_organism", pa.string()),
        pa.field("variant_sequence", pa.string()),
        pa.field("variant_sequence_json", pa.string()),  # Forensic: original JSON
        pa.field("variant_taxonomy_id", pa.float64()),  # Float for nullable int
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
        pa.field("component_accessions", pa.list_(pa.string())),
        pa.field("component_descriptions", pa.list_(pa.string())),
        pa.field("component_id", pa.string()),  # was float64
        pa.field("component_ids", pa.list_(pa.int64())),
        pa.field("component_relationships", pa.list_(pa.string())),
        pa.field("component_types", pa.list_(pa.string())),
        pa.field("cross_references", pa.string()),
        pa.field("downgraded", pa.bool_()),
        pa.field("organism", pa.string()),
        pa.field("pipeline_stages", pa.string()),
        pa.field("pref_name", pa.string()),
        pa.field("species_group_flag", pa.bool_()),
        pa.field("target_id", pa.string()),
        pa.field("target_component_synonyms", pa.string()),
        pa.field("target_components", pa.string()),
        pa.field("target_type", pa.string()),
        pa.field("taxonomy_id", pa.string()),  # was float64
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
        pa.field("component_id", pa.int64()),
        pa.field("component_type", pa.string()),
        pa.field("description", pa.string()),
        pa.field("organism", pa.string()),
        pa.field("primary_component_id", pa.int64()),
        pa.field("protein_classification_id", pa.int64()),
        pa.field("protein_classification_ids", pa.list_(pa.int64())),
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
        pa.field("tissue_chembl_id", pa.string()),  # Primary key
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
        pa.field("entity_id", pa.string()),
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
        pa.field("entity_id", pa.string()),
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
        pa.field("inchi_key", pa.string()),  # Standard InChIKey (matches domain schema)
        pa.field("inorganic_flag", pa.int64()),
        pa.field("max_phase", pa.int64()),
        pa.field("molecule_id", pa.string()),
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
        pa.field("record_id", pa.int64()),
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
        pa.field("sim_id", pa.int64()),
        pa.field("tid_tani", pa.float64()),
        # === DQ_FIELDS_SUFFIX ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
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
        pa.field("_lookup_method", pa.string()),
        pa.field("_original_id", pa.string()),
        pa.field("abstract", pa.string()),
        pa.field("affiliation_list", pa.string()),  # JSON array
        # Author identifiers (for author-level analytics)
        pa.field("author_h_indices", pa.string()),  # JSON array of h-index values
        pa.field("author_orcids", pa.string()),
        pa.field("author_s2_ids", pa.string()),  # JSON array of S2 author IDs
        pa.field("citation_contexts", pa.string()),  # JSON array of context sentences
        pa.field("citations_made", pa.int64()),  # Unified: from referenceCount
        pa.field("citations_received", pa.int64()),  # Unified: from citationCount
        pa.field("corpus_id", pa.int64()),
        pa.field("dblp_id", pa.string()),  # DBLP publication key
        pa.field("doi", pa.string()),
        pa.field("influential_citation_count", pa.int64()),
        pa.field("is_oa", pa.bool_()),
        pa.field("issue", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("oa_status", pa.string()),
        pa.field("open_access_url", pa.string()),
        pa.field("page_first", pa.string()),
        pa.field("page_last", pa.string()),
        pa.field("page_range", pa.string()),  # Page range: "first-last" format
        pa.field("paper_id", pa.string()),  # Primary key
        pa.field(
            "pmc_id", pa.string()
        ),  # PubMed Central ID (inherited from base schema)
        pa.field("pmid", pa.string()),
        pa.field("publication_class", pa.string()),  # Level 1: "EXP" | "REV" | "PEER"
        pa.field("publication_date", pa.string()),
        pa.field(
            "publication_subclass", pa.string()
        ),  # Level 2: "Original Experimental Data", etc.
        pa.field(
            "publication_type", pa.string()
        ),  # Unified: from publicationTypes (joined)
        pa.field(
            "publication_type_unified", pa.string()
        ),  # Level 3: "Journal Article", etc.
        pa.field("publication_types", pa.string()),  # Raw publicationTypes (JSON array)
        pa.field("publication_year", pa.int64()),
        pa.field("subject_fields", pa.string()),
        pa.field("title", pa.string()),
        pa.field("tldr", pa.string()),
        pa.field("volume", pa.string()),
        # === DQ suffix (MUST be last, if present) ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
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
        # Note: abstract and affiliation_list not provided by CrossRef but required by PublicationBaseSchema
        pa.field("abstract", pa.string()),  # Not available from CrossRef (None values)
        pa.field(
            "affiliation_list", pa.string()
        ),  # Not available from CrossRef (None values)
        pa.field("alternative_id", pa.list_(pa.string())),  # Publisher-specific IDs
        pa.field("author_details", pa.string()),  # JSON array of author objects
        pa.field("author_orcids", pa.string()),
        pa.field("authors", pa.string()),  # JSON-serialized list
        pa.field("citations_made", pa.int64()),  # Unified: from references-count
        pa.field(
            "citations_received", pa.int64()
        ),  # Unified: from is-referenced-by-count
        pa.field("content_domain_crossmark_restriction", pa.bool_()),
        pa.field("content_domain_domains", pa.list_(pa.string())),
        # Note: doc_type excluded; CrossRef uses raw 'type' field instead
        # doi: Digital Object Identifier (lowercase, without "https://doi.org/") - Primary key
        pa.field("doi", pa.string()),
        pa.field("issn", pa.string()),
        pa.field("issn_electronic", pa.string()),  # Electronic ISSN
        pa.field("issn_list", pa.string()),  # JSON array of all ISSNs
        pa.field("issn_print", pa.string()),  # Print ISSN
        pa.field("issue", pa.string()),
        pa.field("journal", pa.string()),
        pa.field("journal_name_short", pa.string()),
        pa.field("language", pa.string()),
        pa.field("license_url", pa.string()),
        pa.field("page_first", pa.string()),
        pa.field("page_last", pa.string()),
        # Note: pmid and pmc_id not provided by CrossRef but required by PublicationBaseSchema
        pa.field("pmc_id", pa.string()),  # Not available from CrossRef (None values)
        pa.field("pmid", pa.string()),  # Not available from CrossRef (None values)
        pa.field("publication_class", pa.string()),  # Level 1: "EXP" | "REV" | "PEER"
        pa.field("publication_date", pa.string()),  # Unified: YYYY-MM-DD
        pa.field(
            "publication_subclass", pa.string()
        ),  # Level 2: "Original Experimental Data", etc.
        pa.field(
            "publication_type", pa.string()
        ),  # Raw CrossRef type (journal-article, etc.)
        pa.field(
            "publication_type_unified", pa.string()
        ),  # Level 3: "Journal Article", etc.
        pa.field("publication_year", pa.int64()),
        pa.field("published", pa.string()),  # Canonical publication date
        pa.field("published_online", pa.string()),  # Provider-specific
        pa.field("published_print", pa.string()),  # Provider-specific
        pa.field("publisher", pa.string()),
        pa.field("references", pa.string()),  # JSON array of cited references
        pa.field("subject_keywords", pa.list_(pa.string())),
        pa.field("title", pa.string()),
        pa.field("volume", pa.string()),
        # === DQ suffix (MUST be last, per RULES.md §2.4) ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
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
        pa.field("affiliation_list", pa.string()),  # JSON array
        # Author identifiers (JSON arrays preserving author order)
        pa.field("author_openalex_ids", pa.string()),  # OpenAlex author IDs
        pa.field("author_orcids", pa.string()),
        pa.field("authors", pa.string()),  # JSON-serialized list
        # Unified: from referenced_works_count
        pa.field("citations_made", pa.int64()),
        # OpenAlex source field: cited_by_count
        # Unified BioETL field: citations_received (standardized across all providers)
        pa.field("citations_received", pa.int64()),
        # NOTE: concepts field removed - OpenAlex deprecated concepts in 2024, use topics instead
        # Note: doc_type excluded; OpenAlex uses raw 'type' field instead
        # Cross-reference IDs for linking publications across providers
        # doi: Digital Object Identifier (lowercase, without "https://doi.org/")
        pa.field("doi", pa.string()),
        # Field-Weighted Citation Impact (must be non-negative)
        pa.field("fwci", pa.float64()),
        # Grants/funding information (JSON array)
        pa.field("grants", pa.string()),
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
        pa.field("language", pa.string()),
        # Microsoft Academic Graph ID (legacy, from ids object)
        pa.field("mag_id", pa.string()),
        pa.field("oa_status", pa.string()),
        # Primary key
        pa.field("openalex_id", pa.string()),
        # Unified page fields (from biblio object)
        pa.field("page_first", pa.string()),
        pa.field("page_last", pa.string()),
        # PubMed Central ID - Not available from OpenAlex API (None values)
        pa.field("pmc_id", pa.string()),
        # pmid: PubMed ID (numeric string: "12345678") - nullable, may not exist for all publications
        pa.field("pmid", pa.string()),
        # Primary topic (single most relevant topic for quick categorization)
        pa.field("primary_topic", pa.string()),  # JSON object
        pa.field("publication_class", pa.string()),  # Level 1: "EXP" | "REV" | "PEER"
        pa.field("publication_date", pa.string()),
        pa.field(
            "publication_subclass", pa.string()
        ),  # Level 2: "Original Experimental Data", etc.
        pa.field(
            "publication_type", pa.string()
        ),  # Raw OpenAlex type (article, book, etc.)
        pa.field(
            "publication_type_unified", pa.string()
        ),  # Level 3: "Journal Article", etc.
        pa.field("publication_year", pa.int64()),
        pa.field("publisher", pa.string()),
        # ROR IDs (may be empty if not returned by Works API)
        pa.field("ror_ids", pa.string()),  # JSON array of ROR URLs
        # Keywords extracted from OpenAlex
        pa.field("subject_keywords", pa.list_(pa.string())),
        # MeSH terms extracted from OpenAlex mesh field
        pa.field("subject_mesh", pa.list_(pa.string())),
        # Topics (hierarchical 4-level classification - replaces deprecated concepts)
        pa.field("subject_topics", pa.string()),  # JSON array
        pa.field("title", pa.string()),
        # Bibliographic info (from biblio object)
        pa.field("volume", pa.string()),
        # === DQ suffix (MUST be last, per RULES.md §2.4) ===
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
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
        pa.field("_dq_error", pa.bool_()),
        pa.field("_dq_warn", pa.bool_()),
    ]
)
