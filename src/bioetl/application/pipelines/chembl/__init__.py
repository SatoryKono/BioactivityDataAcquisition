"""ChEMBL pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the ChEMBL database.

Main Components:
- Transformers: ActivityTransformer, AssayTransformer, DocumentSimilarityTransformer, etc.
- BaseChemblTransformer: Base class for ChEMBL-specific transformers
- Pipeline classes: ChEMBLActivityPipeline, ChEMBLAssayPipeline, ChEMBLDocumentSimilarityPipeline, etc.

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
from bioetl.application.pipelines.chembl.document import ChEMBLDocumentPipeline
from bioetl.application.pipelines.chembl.document_similarity import (
    ChEMBLDocumentSimilarityPipeline,
)
from bioetl.application.pipelines.chembl.document_similarity_transformer import (
    DocumentSimilarityTransformer,
)
from bioetl.application.pipelines.chembl.document_term import ChEMBLDocumentTermPipeline
from bioetl.application.pipelines.chembl.document_term_transformer import (
    DocumentTermTransformer,
)
from bioetl.application.pipelines.chembl.document_transformer import (
    DocumentTransformer,
)
from bioetl.application.pipelines.chembl.molecule import ChEMBLMoleculePipeline
from bioetl.application.pipelines.chembl.molecule_transformer import (
    MoleculeTransformer,
)
from bioetl.application.pipelines.chembl.target import ChEMBLTargetPipeline
from bioetl.application.pipelines.chembl.target_component import (
    ChEMBLTargetComponentPipeline,
)
from bioetl.application.pipelines.chembl.target_component_transformer import (
    TargetComponentTransformer,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer

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
    "ChEMBLDocumentPipeline",
    "ChEMBLDocumentSimilarityPipeline",
    "ChEMBLDocumentTermPipeline",
    "ChEMBLMoleculePipeline",
    "ChEMBLTargetComponentPipeline",
    "ChEMBLTargetPipeline",
    "CompoundRecordTransformer",
    "DocumentSimilarityTransformer",
    "DocumentTermTransformer",
    "DocumentTransformer",
    "MoleculeTransformer",
    "TargetComponentTransformer",
    "TargetTransformer",
]
