"""ChEMBL pseudo-null coverage matrix for normalization profiles."""

from __future__ import annotations

from types import MappingProxyType

__all__ = ["CHEMBL_PSEUDO_NULL_FIELDS", "chembl_pseudo_null_fields"]

CHEMBL_PSEUDO_NULL_FIELDS = MappingProxyType(
    {
        "activity": frozenset(
            {
                "action_type",
                "action_type_description",
                "action_type_parent_type",
                "activity_comment",
                "assay_description",
                "assay_type",
                "assay_variant_accession",
                "assay_variant_mutation",
                "bao_endpoint",
                "bao_format",
                "bao_label",
                "canonical_smiles",
                "data_validity_comment",
                "data_validity_description",
                "journal",
                "molecule_pref_name",
                "pchembl_value",
                "publication_doi",
                "publication_pmc_id",
                "publication_pmid",
                "qudt_units",
                "standard_text_value",
                "standard_units",
                "standard_upper_value",
                "standard_value",
                "target_organism",
                "target_pref_name",
                "target_taxonomy_id",
                "text_value",
                "units",
                "uo_units",
                "upper_value",
                "activity_value",
            }
        ),
        "assay": frozenset(
            {
                "assay_category",
                "assay_cell_type",
                "assay_classifications",
                "assay_group",
                "assay_organism",
                "assay_parameters",
                "assay_pref_name",
                "assay_strain",
                "assay_subcellular_fraction",
                "assay_test_type",
                "assay_tissue",
                "assay_type_description",
                "bao_format",
                "bao_label",
                "cell_id",
                "confidence_description",
                "assay_description",
                "publication_id",
                "relationship_description",
                "relationship_type",
                "src_assay_id",
                "target_id",
                "tissue_id",
                "variant_accession",
                "variant_isoform",
                "variant_mutation",
                "variant_organism",
                "variant_sequence",
                "variant_sequence_json",
            }
        ),
        "assay_parameters": frozenset(
            {
                "comments",
                "standard_relation",
                "standard_text_value",
                "standard_type",
                "standard_units",
                "standard_value",
                "text_value",
                "parameter_type",
                "units",
                "parameter_value",
            }
        ),
        "cell_line": frozenset(
            {
                "cell_description",
                "cell_name",
                "cell_source_organism",
                "cell_source_tissue",
                "cell_type",
                "cellosaurus_id",
                "cl_lincs_id",
                "clo_id",
                "efo_id",
            }
        ),
        "compound_record": frozenset(
            {
                "compound_key",
                "compound_name",
                "molecule_id",
                "publication_id",
                "src_compound_id",
            }
        ),
        "molecule": frozenset(
            {
                "atc_classifications",
                "canonical_smiles",
                "cross_references",
                "helm_notation",
                "hierarchy_active_chembl_id",
                "hierarchy_child_chembl_id",
                "hierarchy_parent_chembl_id",
                "inchi_key",
                "logp_method",
                "molecular_formula",
                "molecule_hierarchy",
                "molecule_properties",
                "molecule_species",
                "molecule_structures",
                "molecule_synonyms",
                "pref_name",
                "standard_inchi",
                "usan_stem",
                "usan_stem_definition",
                "usan_substem",
            }
        ),
        "protein_class": frozenset(
            {
                "definition",
                "parent_id",
                "pref_name",
                "protein_class_desc",
                "replaced_by",
                "short_name",
            }
        ),
        "publication": frozenset(
            {
                "abstract",
                "affiliation_list",
                "author_keys",
                "author_orcids",
                "authors",
                "doi",
                "issue",
                "journal",
                "language",
                "oa_status",
                "page_first",
                "page_last",
                "pmc_id",
                "pmid",
                "publication_class",
                "publication_date",
                "publication_doi",
                "publication_pmc_id",
                "publication_pmid",
                "publication_subclass",
                "publication_type",
                "publication_type_raw",
                "publication_type_unified",
                "title",
                "volume",
            }
        ),
        "publication_similarity": frozenset(
            {
                "avg_tani",
                "max_tani",
                "mol_tani",
                "pubmed_id1",
                "pubmed_id2",
                "tid_tani",
            }
        ),
        "publication_term": frozenset({"mesh_id", "qualifier"}),
        "subcellular_fraction": frozenset(
            {
                "assay_count",
                "example_assay_id",
                "subcellular_fraction",
            }
        ),
        "target": frozenset(
            {
                "component_accessions",
                "component_descriptions",
                "component_ids",
                "component_relationships",
                "component_types",
                "cross_references",
                "organism",
                "organism_class",
                "pipeline_stages",
                "pref_name",
                "primary_component_id",
                "target_component_synonyms",
                "target_components",
                "target_description",
                "taxonomy_id",
            }
        ),
        "target_component": frozenset(
            {
                "accession",
                "component_type",
                "component_description",
                "organism",
                "protein_classification_id",
                "protein_classification_ids",
                "protein_classifications",
                "target_component_synonyms",
                "target_component_xrefs",
                "taxonomy_id",
            }
        ),
        "tissue": frozenset(
            {
                "bto_id",
                "caloha_id",
                "efo_id",
                "pref_name",
                "uberon_id",
            }
        ),
    }
)


def chembl_pseudo_null_fields(entity: str) -> frozenset[str]:
    """Return the pseudo-null field matrix row for one ChEMBL entity."""
    return CHEMBL_PSEUDO_NULL_FIELDS.get(entity, frozenset())
