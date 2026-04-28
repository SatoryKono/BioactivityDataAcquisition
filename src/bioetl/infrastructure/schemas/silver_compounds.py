"""PubChem and UniProt Silver layer schemas."""

from __future__ import annotations

__all__ = [
    "PUBCHEM_COMPOUND_SCHEMA",
    "UNIPROT_ID_MAPPING_SCHEMA",
    "UNIPROT_PROTEIN_SCHEMA",
]


import pyarrow as pa

from bioetl.infrastructure.schemas.silver_common_field_blocks import (
    build_silver_dq_suffix_fields,
    build_silver_system_prefix_fields,
)

PUBCHEM_COMPOUND_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        *build_silver_system_prefix_fields(),
        # === Business fields (alphabetical order) ===
        pa.field("canonical_smiles", pa.string()),
        pa.field("molecule_id", pa.string(), nullable=False),
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
        *build_silver_dq_suffix_fields(),
    ]
)

# Schema for UniProt Protein
# Extended schema with functional annotations, cross-references, and quality metrics
# See: https://www.uniprot.org/help/return_fields
UNIPROT_PROTEIN_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        *build_silver_system_prefix_fields(),
        # === Business fields (alphabetical order) ===
        pa.field("accession", pa.string(), nullable=False),  # Primary UniProt accession
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
        *build_silver_dq_suffix_fields(),
    ]
)

# Schema for UniProt ID Mapping
# Maps ChEMBL target IDs to UniProt accessions with entry metadata
UNIPROT_ID_MAPPING_SCHEMA = pa.schema(
    [
        # === System prefix (MUST be first, per RULES.md §2.4) ===
        *build_silver_system_prefix_fields(),
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
        pa.field("target_id", pa.string(), nullable=False),
        pa.field("taxonomy_id", pa.int64()),  # NCBI Taxonomy ID
        # Mapped identifier (nullable - None if not found)
        pa.field("uniprot_accession", pa.string()),
        pa.field("uniprot_entry_name", pa.string()),  # Entry name (e.g., FA10_HUMAN)
        # === DQ suffix (MUST be last, if present) ===
        # DQ warning flag (True for not_found)
        *build_silver_dq_suffix_fields(),
    ]
)

# Schema for PubMed Publication
# Matches Publication entity from domain/entities.py
# See: https://www.nlm.nih.gov/bsd/licensee/elements_descriptions.html
# See also: https://dtd.nlm.nih.gov/ncbi/pubmed/out/pubmed_230101.dtd
