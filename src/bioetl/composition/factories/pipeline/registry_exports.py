"""Public export metadata for the pipeline factory registry."""

from __future__ import annotations

REGISTRY_PUBLIC_EXPORTS: tuple[str, ...] = (
    "PipelineDefinition",
    "PIPELINE_CONFIGS",
    "PipelineFactoryRegistrationState",
    "PipelineRegistry",
    "chembl_activity_factory",
    "chembl_assay_factory",
    "chembl_assay_parameters_factory",
    "chembl_cell_line_factory",
    "chembl_compound_record_factory",
    "chembl_molecule_factory",
    "chembl_protein_class_factory",
    "chembl_publication_factory",
    "chembl_publication_similarity_factory",
    "chembl_publication_term_factory",
    "chembl_subcellular_fraction_factory",
    "chembl_target_component_factory",
    "chembl_target_factory",
    "chembl_tissue_factory",
    "create_pipeline_registration_state",
    "create_registry",
    "crossref_publication_factory",
    "get_factory",
    "get_default_registry",
    "is_registered",
    "list_available_pipelines",
    "openalex_publication_factory",
    "pubchem_compound_factory",
    "pubmed_publication_factory",
    "register_all_pipelines",
    "reset_registration",
    "semanticscholar_publication_factory",
    "uniprot_idmapping_factory",
    "uniprot_protein_factory",
)

# Keep exported compatibility names as the sole list of factory aliases.
FACTORY_EXPORTS: dict[str, str] = {
    name: name.removesuffix("_factory")
    for name in REGISTRY_PUBLIC_EXPORTS
    if name.endswith("_factory") and name != "get_factory"
}

__all__ = [
    "FACTORY_EXPORTS",
    "REGISTRY_PUBLIC_EXPORTS",
]
