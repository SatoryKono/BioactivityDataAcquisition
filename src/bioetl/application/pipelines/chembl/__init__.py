"""ChEMBL pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the ChEMBL database.

Main Components:
- Transformers: ActivityTransformer, AssayTransformer, PublicationSimilarityTransformer, etc.
- BaseChemblTransformer: Base class for ChEMBL-specific transformers
- Pipeline classes: ChEMBLActivityPipeline, ChEMBLAssayPipeline, ChEMBLPublicationSimilarityPipeline, etc.

Usage:
    # Use transformers for custom pipelines
    from bioetl.application.pipelines.chembl import ActivityTransformer
    transformer = ActivityTransformer(provider="chembl")

    # Use pipeline classes for standard pipelines
    from bioetl.application.pipelines.chembl import ChEMBLActivityPipeline
"""

from __future__ import annotations

# Pipeline classes
from bioetl.application.pipelines.chembl.activity import ChEMBLActivityPipeline

# Transformers
from bioetl.application.pipelines.chembl.activity_transformer import (
    ActivityTransformer,
)
from bioetl.application.pipelines.chembl.assay import ChEMBLAssayPipeline
from bioetl.application.pipelines.chembl.assay_parameters import (
    ChEMBLAssayParametersPipeline,
)
from bioetl.application.pipelines.chembl.assay_parameters_transformer import (
    AssayParametersTransformer,
)
from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.application.pipelines.chembl.cell_line import ChEMBLCellLinePipeline
from bioetl.application.pipelines.chembl.cell_line_transformer import (
    CellLineTransformer,
)
from bioetl.application.pipelines.chembl.compound_record import (
    ChEMBLCompoundRecordPipeline,
)
from bioetl.application.pipelines.chembl.compound_record_transformer import (
    CompoundRecordTransformer,
)
from bioetl.application.pipelines.chembl.molecule import ChEMBLMoleculePipeline
from bioetl.application.pipelines.chembl.molecule_transformer import (
    MoleculeTransformer,
)
from bioetl.application.pipelines.chembl.protein_class import (
    ChEMBLProteinClassPipeline,
)
from bioetl.application.pipelines.chembl.protein_class_transformer import (
    ProteinClassTransformer,
)

# Publication pipelines
from bioetl.application.pipelines.chembl.publication import ChEMBLPublicationPipeline
from bioetl.application.pipelines.chembl.publication_similarity import (
    ChEMBLPublicationSimilarityPipeline,
)
from bioetl.application.pipelines.chembl.publication_similarity_transformer import (
    PublicationSimilarityTransformer,
)
from bioetl.application.pipelines.chembl.publication_term import (
    ChEMBLPublicationTermPipeline,
)
from bioetl.application.pipelines.chembl.publication_term_transformer import (
    PublicationTermTransformer,
)
from bioetl.application.pipelines.chembl.publication_transformer import (
    PublicationTransformer,
)
from bioetl.application.pipelines.chembl.target import ChEMBLTargetPipeline
from bioetl.application.pipelines.chembl.target_component import (
    ChEMBLTargetComponentPipeline,
)
from bioetl.application.pipelines.chembl.target_component_transformer import (
    TargetComponentTransformer,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.application.pipelines.chembl.tissue import ChEMBLTissuePipeline
from bioetl.application.pipelines.chembl.tissue_transformer import TissueTransformer

__all__ = [
    "ActivityTransformer",
    "AssayParametersTransformer",
    "AssayTransformer",
    "BaseChemblTransformer",
    "CellLineTransformer",
    "ChEMBLActivityPipeline",
    "ChEMBLAssayParametersPipeline",
    "ChEMBLAssayPipeline",
    "ChEMBLCellLinePipeline",
    "ChEMBLCompoundRecordPipeline",
    "ChEMBLMoleculePipeline",
    "ChEMBLProteinClassPipeline",
    "ChEMBLPublicationPipeline",
    "ChEMBLPublicationSimilarityPipeline",
    "ChEMBLPublicationTermPipeline",
    "ChEMBLTargetComponentPipeline",
    "ChEMBLTargetPipeline",
    "ChEMBLTissuePipeline",
    "CompoundRecordTransformer",
    "MoleculeTransformer",
    "ProteinClassTransformer",
    "PublicationSimilarityTransformer",
    "PublicationTermTransformer",
    "PublicationTransformer",
    "TargetComponentTransformer",
    "TargetTransformer",
    "TissueTransformer",
]
