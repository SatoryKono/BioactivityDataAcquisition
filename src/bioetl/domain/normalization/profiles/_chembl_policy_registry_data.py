"""Published immutable ChEMBL semantic-policy payloads for normalization."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "DEFAULT_CHEMBL_POLICY_REGISTRY_DATA",
    "ChemblControlledVocabularyFamily",
    "ChemblOntologyPolicyFamily",
    "ChemblPolicyRegistryData",
    "ChemblReferenceIdentifierFamily",
    "ChemblStrictScalarFamily",
]


@dataclass(frozen=True, slots=True)
class ChemblControlledVocabularyFamily:
    """Immutable controlled-vocabulary policy for one ChEMBL family."""

    family_name: str
    invalid_value_mode: str
    fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChemblStrictScalarFamily:
    """Immutable strict scalar family for boolean-like and 0/1 flag fields."""

    family_name: str
    invalid_value_mode: str
    fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChemblOntologyPolicyFamily:
    """Immutable ontology/reference policy for one ChEMBL family."""

    family_name: str
    fields: tuple[str, ...]
    companion_governance: str = "full_companion_bundle"
    code_label_fields: tuple[str, ...] = ()
    iri_fields: tuple[str, ...] = ()
    mapping_status_fields: tuple[str, ...] = ()
    version_fields: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ChemblReferenceIdentifierFamily:
    """Immutable reference-identifier policy for one ChEMBL family."""

    family_name: str
    reference_family: str
    invalid_value_mode: str
    fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ChemblPolicyRegistryData:
    """Immutable semantic-policy payload consumed by domain normalization."""

    strict_boolean_families: tuple[ChemblStrictScalarFamily, ...]
    strict_flag_families: tuple[ChemblStrictScalarFamily, ...]
    controlled_vocabularies: tuple[ChemblControlledVocabularyFamily, ...]
    ontology_families: tuple[ChemblOntologyPolicyFamily, ...]
    publication_classification_fields: tuple[str, ...]
    reference_identifier_families: tuple[ChemblReferenceIdentifierFamily, ...] = ()


DEFAULT_CHEMBL_POLICY_REGISTRY_DATA = ChemblPolicyRegistryData(
    strict_boolean_families=(
        ChemblStrictScalarFamily(
            family_name="bool_like",
            invalid_value_mode="coerce_common_boolean_lexemes",
            fields=(
                "chembl_molecule.therapeutic_flag",
                "chembl_molecule.oral",
                "chembl_molecule.parenteral",
                "chembl_molecule.topical",
                "chembl_molecule.withdrawn_flag",
                "chembl_publication.is_oa",
                "chembl_target.species_group_flag",
                "chembl_target.downgraded",
            ),
        ),
    ),
    strict_flag_families=(
        ChemblStrictScalarFamily(
            family_name="binary_flags",
            invalid_value_mode="coerce_common_flag_lexemes",
            fields=(
                "chembl_activity.standard_flag",
                "chembl_activity.potential_duplicate",
                "chembl_activity.manual_curation_flag",
                "chembl_molecule.black_box_warning",
                "chembl_molecule.dosed_ingredient",
                "chembl_molecule.polymer_flag",
                "chembl_protein_class.downgraded",
            ),
        ),
        ChemblStrictScalarFamily(
            family_name="provider_code_flags",
            invalid_value_mode="coerce_reviewed_flag_provider_codes",
            fields=(
                "chembl_molecule.first_in_class",
                "chembl_molecule.inorganic_flag",
                "chembl_molecule.natural_product",
                "chembl_molecule.prodrug",
            ),
        ),
    ),
    controlled_vocabularies=(
        ChemblControlledVocabularyFamily(
            family_name="raw_units",
            invalid_value_mode="preserve_unknown_lexeme",
            fields=(
                "chembl_activity.units",
                "chembl_assay_parameters.units",
            ),
        ),
        ChemblControlledVocabularyFamily(
            family_name="standard_units",
            invalid_value_mode="reject_unknown_lexeme",
            fields=(
                "chembl_activity.standard_units",
                "chembl_assay_parameters.standard_units",
            ),
        ),
        ChemblControlledVocabularyFamily(
            family_name="operators",
            invalid_value_mode="preserve_unknown_lexeme",
            fields=(
                "chembl_activity.relation",
                "chembl_assay_parameters.relation",
            ),
        ),
        ChemblControlledVocabularyFamily(
            family_name="assay_parameter_types",
            invalid_value_mode="preserve_unknown_uppercase_lexeme",
            fields=("chembl_assay_parameters.type",),
        ),
        ChemblControlledVocabularyFamily(
            family_name="assay_categories",
            invalid_value_mode="reject_unknown_lexeme",
            fields=("chembl_assay.assay_category",),
        ),
        ChemblControlledVocabularyFamily(
            family_name="assay_confidence_descriptions",
            invalid_value_mode="reject_unknown_lexeme",
            fields=("chembl_assay.confidence_description",),
        ),
        ChemblControlledVocabularyFamily(
            family_name="target_component_types",
            invalid_value_mode="reject_unknown_json_array_element",
            fields=("chembl_target.component_types",),
        ),
        ChemblControlledVocabularyFamily(
            family_name="target_component_relationships",
            invalid_value_mode="reject_unknown_json_array_element",
            fields=("chembl_target.component_relationships",),
        ),
        ChemblControlledVocabularyFamily(
            family_name="subcellular_fractions",
            invalid_value_mode="preserve_unknown_lexeme",
            fields=(
                "chembl_assay.assay_subcellular_fraction",
                "chembl_subcellular_fraction.subcellular_fraction",
            ),
        ),
    ),
    ontology_families=(
        ChemblOntologyPolicyFamily(
            family_name="bao",
            fields=(
                "chembl_activity.bao_endpoint",
                "chembl_activity.bao_format",
                "chembl_assay.bao_format",
            ),
            code_label_fields=("chembl_assay.bao_label",),
            iri_fields=(
                "chembl_activity.bao_endpoint_iri",
                "chembl_activity.bao_format_iri",
                "chembl_assay.bao_format_iri",
            ),
            mapping_status_fields=(
                "chembl_activity.bao_endpoint_mapping_status",
                "chembl_activity.bao_format_mapping_status",
                "chembl_assay.bao_format_mapping_status",
            ),
            version_fields=(
                "chembl_activity.bao_ontology_version",
                "chembl_assay.bao_ontology_version",
            ),
        ),
        ChemblOntologyPolicyFamily(
            family_name="uo",
            fields=("chembl_activity.uo_units",),
            iri_fields=("chembl_activity.uo_unit_iri",),
            mapping_status_fields=("chembl_activity.uo_unit_mapping_status",),
            version_fields=("chembl_activity.uo_ontology_version",),
        ),
        ChemblOntologyPolicyFamily(
            family_name="qudt",
            fields=("chembl_activity.qudt_units",),
            iri_fields=("chembl_activity.qudt_unit_iri",),
            mapping_status_fields=("chembl_activity.qudt_unit_mapping_status",),
            version_fields=("chembl_activity.qudt_ontology_version",),
        ),
        ChemblOntologyPolicyFamily(
            family_name="bto",
            fields=("chembl_tissue.bto_id",),
            iri_fields=("chembl_tissue.bto_iri",),
            mapping_status_fields=("chembl_tissue.bto_mapping_status",),
            version_fields=("chembl_tissue.bto_ontology_version",),
        ),
        ChemblOntologyPolicyFamily(
            family_name="caloha",
            fields=("chembl_tissue.caloha_id",),
            companion_governance="identifier_only_no_companion_bundle",
        ),
        ChemblOntologyPolicyFamily(
            family_name="efo",
            fields=(
                "chembl_cell_line.efo_id",
                "chembl_tissue.efo_id",
            ),
            iri_fields=(
                "chembl_cell_line.efo_iri",
                "chembl_tissue.efo_iri",
            ),
            mapping_status_fields=(
                "chembl_cell_line.efo_mapping_status",
                "chembl_tissue.efo_mapping_status",
            ),
            version_fields=(
                "chembl_cell_line.efo_ontology_version",
                "chembl_tissue.efo_ontology_version",
            ),
        ),
        ChemblOntologyPolicyFamily(
            family_name="clo",
            fields=("chembl_cell_line.clo_id",),
            iri_fields=("chembl_cell_line.clo_iri",),
            mapping_status_fields=("chembl_cell_line.clo_mapping_status",),
            version_fields=("chembl_cell_line.clo_ontology_version",),
        ),
        ChemblOntologyPolicyFamily(
            family_name="uberon",
            fields=("chembl_tissue.uberon_id",),
            iri_fields=("chembl_tissue.uberon_iri",),
            mapping_status_fields=("chembl_tissue.uberon_mapping_status",),
            version_fields=("chembl_tissue.uberon_ontology_version",),
        ),
        ChemblOntologyPolicyFamily(
            family_name="cellosaurus",
            fields=("chembl_cell_line.cellosaurus_id",),
            companion_governance="identifier_only_no_companion_bundle",
        ),
    ),
    publication_classification_fields=(
        "publication_type_unified",
        "publication_subclass",
        "publication_class",
    ),
    reference_identifier_families=(
        ChemblReferenceIdentifierFamily(
            family_name="chembl",
            reference_family="chembl",
            invalid_value_mode="preserve_unknown_lexeme",
            fields=(
                "chembl_activity.assay_id",
                "chembl_activity.molecule_id",
                "chembl_activity.parent_molecule_id",
                "chembl_activity.publication_id",
                "chembl_activity.target_id",
                "chembl_assay.assay_id",
                "chembl_assay.cell_id",
                "chembl_assay.publication_id",
                "chembl_assay.target_id",
                "chembl_assay.tissue_id",
                "chembl_assay_parameters.assay_id",
                "chembl_cell_line.cell_id",
                "chembl_compound_record.molecule_id",
                "chembl_compound_record.publication_id",
                "chembl_molecule.hierarchy_active_chembl_id",
                "chembl_molecule.hierarchy_child_chembl_id",
                "chembl_molecule.hierarchy_parent_chembl_id",
                "chembl_molecule.molecule_id",
                "chembl_publication.publication_id",
                "chembl_publication_term.publication_id",
                "chembl_subcellular_fraction.example_assay_id",
                "chembl_target.target_id",
                "chembl_tissue.tissue_id",
            ),
        ),
        ChemblReferenceIdentifierFamily(
            family_name="ncbi_taxonomy",
            reference_family="ncbi_taxonomy",
            invalid_value_mode="preserve_numeric_range_for_dq_review",
            fields=(
                "chembl_activity.target_taxonomy_id",
                "chembl_assay.assay_taxonomy_id",
                "chembl_assay.variant_taxonomy_id",
                "chembl_cell_line.cell_source_taxonomy_id",
                "chembl_target.taxonomy_id",
                "chembl_target_component.taxonomy_id",
            ),
        ),
        ChemblReferenceIdentifierFamily(
            family_name="uniprot_accession",
            reference_family="uniprot_accession",
            invalid_value_mode="preserve_unknown_lexeme",
            fields=(
                "chembl_activity.assay_variant_accession",
                "chembl_assay.variant_accession",
                "chembl_target.component_accessions",
                "chembl_target_component.accession",
            ),
        ),
        ChemblReferenceIdentifierFamily(
            family_name="doi",
            reference_family="doi",
            invalid_value_mode="canonicalize_or_null_blank",
            fields=(
                "chembl_activity.publication_doi",
                "chembl_publication.doi",
                "chembl_publication.publication_doi",
            ),
        ),
        ChemblReferenceIdentifierFamily(
            family_name="pmid",
            reference_family="pmid",
            invalid_value_mode="reject_invalid_numeric_identifier",
            fields=(
                "chembl_activity.publication_pmid",
                "chembl_publication.pmid",
                "chembl_publication.publication_pmid",
                "chembl_publication_similarity.pubmed_id1",
                "chembl_publication_similarity.pubmed_id2",
            ),
        ),
        ChemblReferenceIdentifierFamily(
            family_name="pmcid",
            reference_family="pmcid",
            invalid_value_mode="preserve_unknown_lexeme",
            fields=(
                "chembl_activity.publication_pmc_id",
                "chembl_publication.pmc_id",
                "chembl_publication.publication_pmc_id",
            ),
        ),
        ChemblReferenceIdentifierFamily(
            family_name="mesh",
            reference_family="mesh",
            invalid_value_mode="preserve_unknown_lexeme",
            fields=("chembl_publication_term.mesh_id",),
        ),
    ),
)
