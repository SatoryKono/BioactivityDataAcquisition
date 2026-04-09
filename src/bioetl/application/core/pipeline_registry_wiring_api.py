"""Stable application-core seam for composition-owned pipeline registry wiring."""

from __future__ import annotations

from bioetl.application.pipelines.chembl.activity_transformer import ActivityTransformer
from bioetl.application.pipelines.chembl.assay_parameters_transformer import (
    AssayParametersTransformer,
)
from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
from bioetl.application.pipelines.chembl.cell_line_transformer import (
    CellLineTransformer,
)
from bioetl.application.pipelines.chembl.compound_record_transformer import (
    CompoundRecordTransformer,
)
from bioetl.application.pipelines.chembl.molecule_transformer import MoleculeTransformer
from bioetl.application.pipelines.chembl.protein_class_transformer import (
    ProteinClassTransformer,
)
from bioetl.application.pipelines.chembl.publication_similarity_transformer import (
    PublicationSimilarityTransformer,
)
from bioetl.application.pipelines.chembl.publication_term_transformer import (
    PublicationTermTransformer,
)
from bioetl.application.pipelines.chembl.publication_transformer import (
    PublicationTransformer,
)
from bioetl.application.pipelines.chembl.subcellular_fraction_transformer import (
    SubcellularFractionTransformer,
)
from bioetl.application.pipelines.chembl.target_component_transformer import (
    TargetComponentTransformer,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.application.pipelines.chembl.tissue_transformer import TissueTransformer
from bioetl.application.pipelines.crossref.transformer import (
    CrossRefPublicationTransformer,
)
from bioetl.application.pipelines.generic import GenericPipeline
from bioetl.application.pipelines.openalex.transformer import (
    OpenAlexPublicationTransformer,
)
from bioetl.application.pipelines.pubchem.transformer import PubChemCompoundTransformer
from bioetl.application.pipelines.pubmed.transformer import PubMedPublicationTransformer
from bioetl.application.pipelines.semanticscholar.transformer import (
    SemanticScholarPublicationTransformer,
)
from bioetl.application.pipelines.uniprot.idmapping_transformer import (
    IDMappingTransformer,
)
from bioetl.application.pipelines.uniprot.transformer import UniProtProteinTransformer

__all__ = [
    "ActivityTransformer",
    "AssayParametersTransformer",
    "AssayTransformer",
    "CellLineTransformer",
    "CompoundRecordTransformer",
    "CrossRefPublicationTransformer",
    "GenericPipeline",
    "IDMappingTransformer",
    "MoleculeTransformer",
    "OpenAlexPublicationTransformer",
    "ProteinClassTransformer",
    "PubChemCompoundTransformer",
    "PubMedPublicationTransformer",
    "PublicationSimilarityTransformer",
    "PublicationTermTransformer",
    "PublicationTransformer",
    "SemanticScholarPublicationTransformer",
    "SubcellularFractionTransformer",
    "TargetComponentTransformer",
    "TargetTransformer",
    "TissueTransformer",
    "UniProtProteinTransformer",
]
