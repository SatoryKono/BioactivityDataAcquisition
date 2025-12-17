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

# Placeholder for PubChem Compound (expand as needed)
PUBCHEM_COMPOUND_SCHEMA = pa.schema([
    pa.field("entity_id", pa.string()),
    pa.field("compound_id", pa.string()),
    pa.field("content_hash", pa.string()),
    pa.field("_run_id", pa.string()),
    pa.field("_run_type", pa.string()),
    pa.field("_source_batch_id", pa.string()),
    pa.field("_ingestion_ts", pa.string()),
])

# Placeholder for UniProt Protein (expand as needed)
UNIPROT_PROTEIN_SCHEMA = pa.schema([
    pa.field("entity_id", pa.string()),
    pa.field("accession", pa.string()),
    pa.field("content_hash", pa.string()),
    pa.field("_run_id", pa.string()),
    pa.field("_run_type", pa.string()),
    pa.field("_source_batch_id", pa.string()),
    pa.field("_ingestion_ts", pa.string()),
])
