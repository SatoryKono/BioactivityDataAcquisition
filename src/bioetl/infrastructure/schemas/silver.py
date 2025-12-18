"""Silver layer schemas for Delta Lake tables.

Defines the PyArrow schemas for various entities in the Silver layer.
"""

import pyarrow as pa

# Schema for ChEMBL Activity
CHEMBL_ACTIVITY_SCHEMA = pa.schema([
    pa.field("entity_id", pa.string()),
    pa.field("activity_id", pa.string()),
    pa.field("molecule_chembl_id", pa.string()),
    pa.field("target_chembl_id", pa.string()),
    pa.field("assay_chembl_id", pa.string()),
    pa.field("standard_type", pa.string()),
    pa.field("standard_value", pa.float64()),
    pa.field("standard_units", pa.string()),
    pa.field("standard_relation", pa.string()),
    pa.field("assay_type", pa.string()),
    pa.field("assay_description", pa.string()),
    pa.field("document_chembl_id", pa.string()),
    pa.field("document_year", pa.int64()),
    pa.field("pchembl_value", pa.float64()),
    pa.field("activity_comment", pa.string()),
    pa.field("data_validity_comment", pa.string()),
    pa.field("content_hash", pa.string()),
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
