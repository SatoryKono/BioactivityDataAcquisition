"""Silver layer schemas for Delta Lake tables.

Defines the PyArrow schemas for various entities in the Silver layer.
"""

import pyarrow as pa

# Schema for ChEMBL Activity (all fields from ChEMBL API)
# See: https://www.ebi.ac.uk/chembl/api/data/activity
CHEMBL_ACTIVITY_SCHEMA = pa.schema(
    [
        # System fields
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        # Primary identifier
        pa.field("activity_id", pa.string()),
        # Core identifiers
        pa.field("molecule_chembl_id", pa.string()),
        pa.field("target_chembl_id", pa.string()),
        pa.field("assay_chembl_id", pa.string()),
        pa.field("document_chembl_id", pa.string()),
        pa.field("record_id", pa.int64()),
        pa.field("src_id", pa.int64()),
        # Molecule data
        pa.field("canonical_smiles", pa.string()),
        pa.field("molecule_pref_name", pa.string()),
        pa.field("parent_molecule_chembl_id", pa.string()),
        # Target data
        pa.field("target_pref_name", pa.string()),
        pa.field("target_organism", pa.string()),
        pa.field("target_tax_id", pa.string()),
        # Assay data
        pa.field("assay_type", pa.string()),
        pa.field("assay_description", pa.string()),
        pa.field("assay_variant_accession", pa.string()),
        pa.field("assay_variant_mutation", pa.string()),
        # BAO (BioAssay Ontology) annotations
        pa.field("bao_endpoint", pa.string()),
        pa.field("bao_format", pa.string()),
        pa.field("bao_label", pa.string()),
        # Raw activity values
        pa.field("type", pa.string()),
        pa.field("value", pa.float64()),
        pa.field("units", pa.string()),
        pa.field("relation", pa.string()),
        pa.field("upper_value", pa.float64()),
        pa.field("text_value", pa.string()),
        # Standardized activity values
        pa.field("standard_type", pa.string()),
        pa.field("standard_value", pa.float64()),
        pa.field("standard_units", pa.string()),
        pa.field("standard_relation", pa.string()),
        pa.field("standard_upper_value", pa.float64()),
        pa.field("standard_text_value", pa.string()),
        pa.field("standard_flag", pa.int64()),
        # Derived metrics
        pa.field("pchembl_value", pa.float64()),
        pa.field("ligand_efficiency", pa.string()),  # JSON string
        # Units ontology
        pa.field("qudt_units", pa.string()),
        pa.field("uo_units", pa.string()),
        # Document/Publication data
        pa.field("document_journal", pa.string()),
        pa.field("document_year", pa.int64()),
        # Quality annotations
        pa.field("activity_comment", pa.string()),
        pa.field("data_validity_comment", pa.string()),
        pa.field("data_validity_description", pa.string()),
        pa.field("potential_duplicate", pa.int64()),
        # Action and properties
        pa.field("action_type", pa.string()),
        pa.field("activity_properties", pa.string()),  # JSON string
        pa.field("toid", pa.int64()),
        # Lineage metadata
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
    ]
)

# Schema for PubChem Compound
PUBCHEM_COMPOUND_SCHEMA = pa.schema(
    [
        pa.field("entity_id", pa.string()),
        pa.field("cid", pa.string()),
        pa.field("molecular_formula", pa.string()),
        pa.field("molecular_weight", pa.string()),  # Stored as string from source
        pa.field("canonical_smiles", pa.string()),
        pa.field("isomeric_smiles", pa.string()),
        pa.field("inchi", pa.string()),
        pa.field("inchikey", pa.string()),
        pa.field("iupac_name", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
    ]
)

# Schema for UniProt Protein
UNIPROT_PROTEIN_SCHEMA = pa.schema(
    [
        pa.field("entity_id", pa.string()),
        pa.field("accession", pa.string()),
        pa.field("entry_name", pa.string()),
        pa.field("protein_name", pa.string()),
        pa.field("gene_names", pa.list_(pa.string())),
        pa.field("organism_id", pa.int64()),
        pa.field("sequence_length", pa.int64()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
    ]
)

# Schema for PubMed Publication
PUBMED_PUBLICATION_SCHEMA = pa.schema(
    [
        pa.field("entity_id", pa.string()),
        pa.field("pmid", pa.string()),
        pa.field("article_title", pa.string()),
        pa.field("content_hash", pa.string()),
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
    ]
)

# Schema for ChEMBL Assay
# See: https://www.ebi.ac.uk/chembl/api/data/assay
CHEMBL_ASSAY_SCHEMA = pa.schema(
    [
        # System fields
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        # Primary identifier
        pa.field("assay_chembl_id", pa.string()),
        # Core identifiers
        pa.field("target_chembl_id", pa.string()),
        pa.field("document_chembl_id", pa.string()),
        pa.field("cell_chembl_id", pa.string()),
        pa.field("tissue_chembl_id", pa.string()),
        pa.field("src_id", pa.int64()),
        pa.field("src_assay_id", pa.string()),
        pa.field("aidx", pa.string()),
        # Assay classification
        pa.field("assay_type", pa.string()),
        pa.field("assay_type_description", pa.string()),
        pa.field("assay_category", pa.string()),
        pa.field("assay_test_type", pa.string()),
        pa.field("assay_group", pa.string()),
        # Biological context
        pa.field("assay_organism", pa.string()),
        pa.field("assay_tax_id", pa.int64()),
        pa.field("assay_cell_type", pa.string()),
        pa.field("assay_tissue", pa.string()),
        pa.field("assay_strain", pa.string()),
        pa.field("assay_subcellular_fraction", pa.string()),
        # BAO (BioAssay Ontology) annotations
        pa.field("bao_format", pa.string()),
        pa.field("bao_label", pa.string()),
        # Description and confidence
        pa.field("description", pa.string()),
        pa.field("confidence_score", pa.int64()),
        pa.field("confidence_description", pa.string()),
        pa.field("relationship_type", pa.string()),
        pa.field("relationship_description", pa.string()),
        # Variant information
        pa.field("variant_sequence", pa.string()),
        # Complex fields (stored as JSON strings)
        pa.field("assay_classifications", pa.string()),  # JSON string
        pa.field("assay_parameters", pa.string()),  # JSON string
        # Lineage metadata
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
    ]
)

# Schema for ChEMBL Target
# See: https://www.ebi.ac.uk/chembl/api/data/target
CHEMBL_TARGET_SCHEMA = pa.schema(
    [
        # System fields
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        # Primary identifier
        pa.field("target_chembl_id", pa.string()),
        # Core metadata
        pa.field("pref_name", pa.string()),
        pa.field("target_type", pa.string()),
        pa.field("organism", pa.string()),
        pa.field("tax_id", pa.int64()),
        pa.field("species_group_flag", pa.bool_()),
        # Complex fields (JSON strings)
        pa.field("target_components", pa.string()),
        pa.field("cross_references", pa.string()),
        # Lineage metadata
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
    ]
)

# Schema for ChEMBL Document
# See: https://www.ebi.ac.uk/chembl/api/data/document
CHEMBL_DOCUMENT_SCHEMA = pa.schema(
    [
        # System fields
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        # Primary identifier
        pa.field("document_chembl_id", pa.string()),
        # Publication identifiers
        pa.field("pubmed_id", pa.int64()),
        pa.field("doi", pa.string()),
        pa.field("patent_id", pa.string()),
        # Core metadata
        pa.field("title", pa.string()),
        pa.field("authors", pa.string()),
        pa.field("abstract", pa.string()),
        pa.field("doc_type", pa.string()),
        # Journal information
        pa.field("journal", pa.string()),
        pa.field("journal_full_title", pa.string()),
        pa.field("year", pa.int64()),
        pa.field("volume", pa.string()),
        pa.field("issue", pa.string()),
        pa.field("first_page", pa.string()),
        pa.field("last_page", pa.string()),
        # Source information
        pa.field("src_id", pa.int64()),
        # Lineage metadata
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
    ]
)

# Schema for ChEMBL Molecule
# See: https://www.ebi.ac.uk/chembl/api/data/molecule
CHEMBL_MOLECULE_SCHEMA = pa.schema(
    [
        # System fields
        pa.field("entity_id", pa.string()),
        pa.field("content_hash", pa.string()),
        # Primary identifier
        pa.field("molecule_chembl_id", pa.string()),
        # Core metadata
        pa.field("pref_name", pa.string()),
        pa.field("molecule_type", pa.string()),
        pa.field("structure_type", pa.string()),
        pa.field("max_phase", pa.int64()),
        pa.field("first_approval", pa.int64()),
        # Flags
        pa.field("oral", pa.bool_()),
        pa.field("parenteral", pa.bool_()),
        pa.field("topical", pa.bool_()),
        pa.field("black_box_warning", pa.int64()),
        pa.field("natural_product", pa.int64()),
        pa.field("first_in_class", pa.int64()),
        pa.field("prodrug", pa.int64()),
        pa.field("therapeutic_flag", pa.bool_()),
        pa.field("withdrawn_flag", pa.bool_()),
        pa.field("inorganic_flag", pa.int64()),
        pa.field("polymer_flag", pa.int64()),
        # Complex fields (JSON strings)
        pa.field("molecule_hierarchy", pa.string()),
        pa.field("molecule_properties", pa.string()),
        pa.field("molecule_structures", pa.string()),
        pa.field("molecule_synonyms", pa.string()),
        pa.field("cross_references", pa.string()),
        pa.field("atc_classifications", pa.string()),
        # Lineage metadata
        pa.field("_run_id", pa.string()),
        pa.field("_run_type", pa.string()),
        pa.field("_source_batch_id", pa.string()),
        pa.field("_ingestion_ts", pa.string()),
    ]
)
