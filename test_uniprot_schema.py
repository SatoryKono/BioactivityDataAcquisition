import pandas as pd
import pandera.pandas as pa
from bioetl.domain.schemas.uniprot.protein import ProteinSchema
from datetime import date, datetime, UTC
from uuid import uuid4

def test_uniprot_protein_validation():
    # Order from schema:
    # ETLRecordSchema fields: entity_id, content_hash, _run_id, _run_type, _source_batch_id, _ingestion_ts, _dq_warn, _dq_error, _index
    # ProteinSchema fields: accession, entry_name, entry_type, secondary_accessions, protein_name, protein_short_names, 
    # protein_alternative_names, protein_ec_numbers, flag, gene_primary, gene_synonyms, gene_orf_names,
    # organism_scientific, organism_common, taxonomy_id, lineage, protein_existence, annotation_score, reviewed,
    # sequence, sequence_length, sequence_mass, sequence_checksum, sequence_modified, entry_version, entry_created, entry_modified,
    # function_comment, catalytic_activity, activity_regulation, subunit, pathway, subcellular_location,
    # tissue_specificity, alternative_products, disease_involvement, pharmaceutical_use, similarity_comment, caution,
    # go_terms, drugbank_ids, chembl_ids, guidetopharmacology_ids, features, keywords,
    # cross_reference_count, feature_count, keyword_count, publication_count, isoform_count

    data = {
        "entity_id": "uniprot:P12345",
        "content_hash": "a" * 64,
        "_run_id": uuid4(),
        "_run_type": "incremental",
        "_source_batch_id": None,
        "_ingestion_ts": datetime.now(UTC),
        "_dq_warn": False,
        "_dq_error": False,
        "_index": 0,
        "accession": "P12345",
        "entry_name": "TEST_PROT",
        "entry_type": None,
        "secondary_accessions": None,
        "protein_name": "Test Protein",
        "protein_short_names": None,
        "protein_alternative_names": None,
        "protein_ec_numbers": None,
        "flag": None,
        "gene_primary": None,
        "gene_synonyms": None,
        "gene_orf_names": None,
        "organism_scientific": None,
        "organism_common": None,
        "taxonomy_id": 9606,
        "lineage": None,
        "protein_existence": None,
        "annotation_score": 5,
        "reviewed": True,
        "sequence": "ACDEFGHIKLMNPQRSTVWY",
        "sequence_length": 20,
        "sequence_mass": 2000,
        "sequence_checksum": "CRC123",
        "sequence_modified": date(2024, 1, 1),
        "entry_version": 1,
        "entry_created": date(2024, 1, 1),
        "entry_modified": date(2024, 1, 1),
        "function_comment": None,
        "catalytic_activity": None,
        "activity_regulation": None,
        "subunit": None,
        "pathway": None,
        "subcellular_location": None,
        "tissue_specificity": None,
        "alternative_products": None,
        "disease_involvement": None,
        "pharmaceutical_use": None,
        "similarity_comment": None,
        "caution": None,
        "go_terms": None,
        "drugbank_ids": None,
        "chembl_ids": None,
        "guidetopharmacology_ids": None,
        "features": None,
        "keywords": None,
        "cross_reference_count": 0,
        "feature_count": 0,
        "keyword_count": 0,
        "publication_count": 0,
        "isoform_count": 0,
    }
    df = pd.DataFrame([data])
    # Ensure columns are in correct order
    cols = list(data.keys())
    df = df[cols]
    
    try:
        ProteinSchema.validate(df)
        print("Validation successful")
    except Exception as e:
        print(f"Validation failed: {e}")
        # import traceback
        # traceback.print_exc()

if __name__ == "__main__":
    test_uniprot_protein_validation()
