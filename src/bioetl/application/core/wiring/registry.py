"""Stable application-core seam for composition-owned pipeline registry wiring.

This compatibility facade preserves historical imports without eagerly importing
every pipeline transformer during module initialization. Static exports are
declared in the adjacent stub.
"""

from __future__ import annotations

from bioetl.application.core.wiring._lazy_export_facade import (
    install_lazy_export_facade,
)

_PUBLIC_EXPORTS = {
    "ActivityTransformer": "bioetl.application.pipelines.chembl.activity_transformer",
    "AssayParametersTransformer": (
        "bioetl.application.pipelines.chembl.assay_parameters_transformer"
    ),
    "AssayTransformer": "bioetl.application.pipelines.chembl.assay_transformer",
    "CellLineTransformer": "bioetl.application.pipelines.chembl.cell_line_transformer",
    "CompoundRecordTransformer": (
        "bioetl.application.pipelines.chembl.compound_record_transformer"
    ),
    "CrossRefPublicationTransformer": (
        "bioetl.application.pipelines.crossref.transformer"
    ),
    "GenericPipeline": "bioetl.application.pipelines.generic",
    "IDMappingTransformer": (
        "bioetl.application.pipelines.uniprot.idmapping_transformer"
    ),
    "MoleculeTransformer": "bioetl.application.pipelines.chembl.molecule_transformer",
    "OpenAlexPublicationTransformer": "bioetl.application.pipelines.openalex.transformer",
    "ProteinClassTransformer": (
        "bioetl.application.pipelines.chembl.protein_class_transformer"
    ),
    "PubChemCompoundTransformer": "bioetl.application.pipelines.pubchem.transformer",
    "PubMedPublicationTransformer": "bioetl.application.pipelines.pubmed.transformer",
    "PublicationSimilarityTransformer": (
        "bioetl.application.pipelines.chembl.publication_similarity_transformer"
    ),
    "PublicationTermTransformer": (
        "bioetl.application.pipelines.chembl.publication_term_transformer"
    ),
    "PublicationTransformer": (
        "bioetl.application.pipelines.chembl.publication_transformer"
    ),
    "SemanticScholarPublicationTransformer": (
        "bioetl.application.pipelines.semanticscholar.transformer"
    ),
    "SubcellularFractionTransformer": (
        "bioetl.application.pipelines.chembl.subcellular_fraction_transformer"
    ),
    "TargetComponentTransformer": (
        "bioetl.application.pipelines.chembl.target_component_transformer"
    ),
    "TargetProteinClassificationTransformer": (
        "bioetl.application.pipelines.chembl.target_protein_classification_transformer"
    ),
    "TargetTransformer": "bioetl.application.pipelines.chembl.target_transformer",
    "TissueTransformer": "bioetl.application.pipelines.chembl.tissue_transformer",
    "UniProtProteinTransformer": "bioetl.application.pipelines.uniprot.transformer",
}

install_lazy_export_facade(globals(), __name__, _PUBLIC_EXPORTS)

__all__: list[str]
