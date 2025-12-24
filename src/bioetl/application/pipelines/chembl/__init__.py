"""ChEMBL pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the ChEMBL database.
"""

from __future__ import annotations

from bioetl.application.pipelines.chembl.activity import ChEMBLActivityPipeline
from bioetl.application.pipelines.chembl.activity_transformer import (
    ActivityTransformer,
)
from bioetl.application.pipelines.chembl.assay import ChEMBLAssayPipeline
from bioetl.application.pipelines.chembl.assay_transformer import AssayTransformer
from bioetl.application.pipelines.chembl.document import ChEMBLDocumentPipeline
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
    # Transformers
    "ActivityTransformer",
    "AssayTransformer",
    # Pipelines
    "ChEMBLActivityPipeline",
    "ChEMBLAssayPipeline",
    "ChEMBLDocumentPipeline",
    "ChEMBLMoleculePipeline",
    "ChEMBLTargetComponentPipeline",
    "ChEMBLTargetPipeline",
    "DocumentTransformer",
    "MoleculeTransformer",
    "TargetComponentTransformer",
    "TargetTransformer",
]
