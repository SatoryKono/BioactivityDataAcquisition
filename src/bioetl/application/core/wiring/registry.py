"""Stable application-core seam for composition-owned pipeline registry wiring.

This compatibility facade preserves historical imports without eagerly importing
every pipeline transformer during module initialization.
"""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

_PUBLIC_EXPORTS = {
    "ActivityTransformer": (
        "bioetl.application.pipelines.chembl.activity_transformer",
        "ActivityTransformer",
    ),
    "AssayParametersTransformer": (
        "bioetl.application.pipelines.chembl.assay_parameters_transformer",
        "AssayParametersTransformer",
    ),
    "AssayTransformer": (
        "bioetl.application.pipelines.chembl.assay_transformer",
        "AssayTransformer",
    ),
    "CellLineTransformer": (
        "bioetl.application.pipelines.chembl.cell_line_transformer",
        "CellLineTransformer",
    ),
    "CompoundRecordTransformer": (
        "bioetl.application.pipelines.chembl.compound_record_transformer",
        "CompoundRecordTransformer",
    ),
    "CrossRefPublicationTransformer": (
        "bioetl.application.pipelines.crossref.transformer",
        "CrossRefPublicationTransformer",
    ),
    "GenericPipeline": (
        "bioetl.application.pipelines.generic",
        "GenericPipeline",
    ),
    "IDMappingTransformer": (
        "bioetl.application.pipelines.uniprot.idmapping_transformer",
        "IDMappingTransformer",
    ),
    "MoleculeTransformer": (
        "bioetl.application.pipelines.chembl.molecule_transformer",
        "MoleculeTransformer",
    ),
    "OpenAlexPublicationTransformer": (
        "bioetl.application.pipelines.openalex.transformer",
        "OpenAlexPublicationTransformer",
    ),
    "ProteinClassTransformer": (
        "bioetl.application.pipelines.chembl.protein_class_transformer",
        "ProteinClassTransformer",
    ),
    "PubChemCompoundTransformer": (
        "bioetl.application.pipelines.pubchem.transformer",
        "PubChemCompoundTransformer",
    ),
    "PubMedPublicationTransformer": (
        "bioetl.application.pipelines.pubmed.transformer",
        "PubMedPublicationTransformer",
    ),
    "PublicationSimilarityTransformer": (
        "bioetl.application.pipelines.chembl.publication_similarity_transformer",
        "PublicationSimilarityTransformer",
    ),
    "PublicationTermTransformer": (
        "bioetl.application.pipelines.chembl.publication_term_transformer",
        "PublicationTermTransformer",
    ),
    "PublicationTransformer": (
        "bioetl.application.pipelines.chembl.publication_transformer",
        "PublicationTransformer",
    ),
    "SemanticScholarPublicationTransformer": (
        "bioetl.application.pipelines.semanticscholar.transformer",
        "SemanticScholarPublicationTransformer",
    ),
    "SubcellularFractionTransformer": (
        "bioetl.application.pipelines.chembl.subcellular_fraction_transformer",
        "SubcellularFractionTransformer",
    ),
    "TargetComponentTransformer": (
        "bioetl.application.pipelines.chembl.target_component_transformer",
        "TargetComponentTransformer",
    ),
    "TargetTransformer": (
        "bioetl.application.pipelines.chembl.target_transformer",
        "TargetTransformer",
    ),
    "TissueTransformer": (
        "bioetl.application.pipelines.chembl.tissue_transformer",
        "TissueTransformer",
    ),
    "UniProtProteinTransformer": (
        "bioetl.application.pipelines.uniprot.transformer",
        "UniProtProteinTransformer",
    ),
}

__all__ = list(_PUBLIC_EXPORTS)


def __getattr__(name: str) -> object:
    export = _PUBLIC_EXPORTS.get(name)
    if export is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attr_name = export
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
