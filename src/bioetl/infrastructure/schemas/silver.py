"""Silver layer schemas for Delta Lake tables.

Defines the PyArrow schemas for various entities in the Silver layer.
"""

import pyarrow as pa

# Schema for ChEMBL Activity (all fields from ChEMBL API)
# See: https://www.ebi.ac.uk/chembl/api/data/activity
CHEMBL_ACTIVITY_SCHEMA = pa.schema([
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
])

# Schema for PubChem Compound
PUBCHEM_COMPOUND_SCHEMA = pa.schema([
    pa.field("entity_id", pa.string()),
    pa.field("cid", pa.string()),
    pa.field("molecular_formula", pa.string()),
    pa.field("molecular_weight", pa.string()), # Stored as string from source
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
])

# Schema for UniProt Protein
UNIPROT_PROTEIN_SCHEMA = pa.schema([
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
])

# Schema for PubMed Publication
PUBMED_PUBLICATION_SCHEMA = pa.schema([
    pa.field("entity_id", pa.string()),
    pa.field("pmid", pa.string()),
    pa.field("article_title", pa.string()),
    pa.field("content_hash", pa.string()),
    pa.field("_run_id", pa.string()),
    pa.field("_run_type", pa.string()),
    pa.field("_source_batch_id", pa.string()),
    pa.field("_ingestion_ts", pa.string()),
])
