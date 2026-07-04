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

from bioetl.application.pipelines.chembl import pipeline_types as _pipeline_types

# Transformers
from bioetl.application.pipelines.chembl.activity_transformer import (
    ActivityTransformer,
)
from bioetl.application.pipelines.chembl.assay_parameters_transformer import (
    AssayParametersTransformer,
)
from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.application.pipelines.chembl.cell_line_transformer import (
    CellLineTransformer,
)
from bioetl.application.pipelines.chembl.compound_record_transformer import (
    CompoundRecordTransformer,
)
from bioetl.application.pipelines.chembl.molecule_transformer import (
    MoleculeTransformer,
)

# Pipeline marker classes (canonical owner: pipeline_types.py)
from bioetl.application.pipelines.chembl.pipeline_types import (
    ChEMBLActivityPipeline as ChEMBLActivityPipeline,
)
from bioetl.application.pipelines.chembl.pipeline_types import (
    ChEMBLAssayParametersPipeline as ChEMBLAssayParametersPipeline,
)
from bioetl.application.pipelines.chembl.pipeline_types import (
    ChEMBLAssayPipeline as ChEMBLAssayPipeline,
)
from bioetl.application.pipelines.chembl.pipeline_types import (
    ChEMBLCellLinePipeline as ChEMBLCellLinePipeline,
)
from bioetl.application.pipelines.chembl.pipeline_types import (
    ChEMBLCompoundRecordPipeline as ChEMBLCompoundRecordPipeline,
)
from bioetl.application.pipelines.chembl.pipeline_types import (
    ChEMBLMoleculePipeline as ChEMBLMoleculePipeline,
)
from bioetl.application.pipelines.chembl.pipeline_types import (
    ChEMBLProteinClassPipeline as ChEMBLProteinClassPipeline,
)
from bioetl.application.pipelines.chembl.pipeline_types import (
    ChEMBLPublicationPipeline as ChEMBLPublicationPipeline,
)
from bioetl.application.pipelines.chembl.pipeline_types import (
    ChEMBLPublicationSimilarityPipeline as ChEMBLPublicationSimilarityPipeline,
)
from bioetl.application.pipelines.chembl.pipeline_types import (
    ChEMBLPublicationTermPipeline as ChEMBLPublicationTermPipeline,
)
from bioetl.application.pipelines.chembl.pipeline_types import (
    ChEMBLSubcellularFractionPipeline as ChEMBLSubcellularFractionPipeline,
)
from bioetl.application.pipelines.chembl.pipeline_types import (
    ChEMBLTargetComponentPipeline as ChEMBLTargetComponentPipeline,
)
from bioetl.application.pipelines.chembl.pipeline_types import (
    ChEMBLTargetPipeline as ChEMBLTargetPipeline,
)
from bioetl.application.pipelines.chembl.pipeline_types import (
    ChEMBLTargetProteinClassificationPipeline as ChEMBLTargetProteinClassificationPipeline,
)
from bioetl.application.pipelines.chembl.pipeline_types import (
    ChEMBLTissuePipeline as ChEMBLTissuePipeline,
)
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
from bioetl.application.pipelines.chembl.target_protein_classification_transformer import (
    TargetProteinClassificationTransformer,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.application.pipelines.chembl.tissue_transformer import TissueTransformer

__all__ = [
    "ActivityTransformer",
    "AssayParametersTransformer",
    "AssayTransformer",
    "BaseChemblTransformer",
    "CellLineTransformer",
    "CompoundRecordTransformer",
    "MoleculeTransformer",
    "ProteinClassTransformer",
    "PublicationSimilarityTransformer",
    "PublicationTermTransformer",
    "PublicationTransformer",
    "SubcellularFractionTransformer",
    "TargetComponentTransformer",
    "TargetProteinClassificationTransformer",
    "TargetTransformer",
    "TissueTransformer",
    *_pipeline_types.__all__,
]
