# mypy: ignore-errors
"""AUTO-GENERATED FILE. DO NOT EDIT MANUALLY."""

# mypy: ignore-errors
from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series

class UniprotProteinSilverSchema(pa.DataFrameModel):
    """Generated Pandera schema from canonical schema registry."""

    entity_id: Series[str] | None = pa.Field(nullable=True)
    content_hash: Series[str] | None = pa.Field(nullable=True)
    _run_id: Series[str] | None = pa.Field(nullable=True)
    _run_type: Series[str] | None = pa.Field(nullable=True)
    _source_batch_id: Series[str] | None = pa.Field(nullable=True)
    _ingestion_ts: Series[str] | None = pa.Field(nullable=True)
    _index: Series[int] | None = pa.Field(nullable=True)
    accession: Series[str] | None = pa.Field(nullable=True)
    acetylation: Series[str] | None = pa.Field(nullable=True)
    active_sites: Series[str] | None = pa.Field(nullable=True)
    activity_regulation: Series[str] | None = pa.Field(nullable=True)
    annotation_score: Series[int] | None = pa.Field(nullable=True)
    binding_sites: Series[str] | None = pa.Field(nullable=True)
    catalytic_activity: Series[str] | None = pa.Field(nullable=True)
    cellular_component: Series[str] | None = pa.Field(nullable=True)
    chembl_ids: Series[str] | None = pa.Field(nullable=True)
    disease_involvement: Series[str] | None = pa.Field(nullable=True)
    disulfide_bond: Series[str] | None = pa.Field(nullable=True)
    domains: Series[str] | None = pa.Field(nullable=True)
    drugbank_ids: Series[str] | None = pa.Field(nullable=True)
    entry_name: Series[str] | None = pa.Field(nullable=True)
    features_json: Series[str] | None = pa.Field(nullable=True)
    function_comment: Series[str] | None = pa.Field(nullable=True)
    genus: Series[str] | None = pa.Field(nullable=True)
    glycosylation: Series[str] | None = pa.Field(nullable=True)
    go_terms: Series[str] | None = pa.Field(nullable=True)
    interpro_xrefs: Series[str] | None = pa.Field(nullable=True)
    intramembrane: Series[str] | None = pa.Field(nullable=True)
    isoform_ids: Series[str] | None = pa.Field(nullable=True)
    isoform_names: Series[str] | None = pa.Field(nullable=True)
    isoform_synonyms: Series[str] | None = pa.Field(nullable=True)
    lipidation: Series[str] | None = pa.Field(nullable=True)
    modified_residue: Series[str] | None = pa.Field(nullable=True)
    molecular_function: Series[str] | None = pa.Field(nullable=True)
    organism_id: Series[int] | None = pa.Field(nullable=True)
    pathway: Series[str] | None = pa.Field(nullable=True)
    pdb_xrefs: Series[str] | None = pa.Field(nullable=True)
    pfam_xrefs: Series[str] | None = pa.Field(nullable=True)
    phosphorylation: Series[str] | None = pa.Field(nullable=True)
    phylum: Series[str] | None = pa.Field(nullable=True)
    propeptide: Series[str] | None = pa.Field(nullable=True)
    protein_existence: Series[str] | None = pa.Field(nullable=True)
    protein_name: Series[str] | None = pa.Field(nullable=True)
    reaction_ec_numbers: Series[str] | None = pa.Field(nullable=True)
    reactions: Series[str] | None = pa.Field(nullable=True)
    reactome_xrefs: Series[str] | None = pa.Field(nullable=True)
    reviewed: Series[bool] | None = pa.Field(nullable=True)
    sequence_length: Series[int] | None = pa.Field(nullable=True)
    signal_peptide: Series[str] | None = pa.Field(nullable=True)
    similarity_comment: Series[str] | None = pa.Field(nullable=True)
    subcellular_location: Series[str] | None = pa.Field(nullable=True)
    superkingdom: Series[str] | None = pa.Field(nullable=True)
    tissue_specificity: Series[str] | None = pa.Field(nullable=True)
    topology: Series[str] | None = pa.Field(nullable=True)
    transmembrane: Series[str] | None = pa.Field(nullable=True)
    ubiquitination: Series[str] | None = pa.Field(nullable=True)
    _dq_error: Series[bool] | None = pa.Field(nullable=True)
    _dq_warn: Series[bool] | None = pa.Field(nullable=True)

    class Config:
        strict = True
        ordered = True
        coerce = True
