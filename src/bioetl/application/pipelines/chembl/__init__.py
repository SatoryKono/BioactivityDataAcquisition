"""ChEMBL pipeline components.

This package provides pipelines and transformers for extracting and
processing data from the ChEMBL database.

Main Components:
- Transformers: ActivityTransformer, AssayTransformer, etc.
- BaseChemblTransformer: Base class for ChEMBL-specific transformers
- Deprecated pipeline aliases: ChEMBLActivityPipeline, etc.

Usage:
    # Recommended - use transformers directly
    from bioetl.application.pipelines.chembl import ActivityTransformer
    transformer = ActivityTransformer(provider="chembl")

    # Deprecated - pipeline classes (will emit DeprecationWarning)
    from bioetl.application.pipelines.chembl import ChEMBLActivityPipeline
"""

from __future__ import annotations

# Transformers (actively used)
from bioetl.application.pipelines.chembl.activity_transformer import (
    ActivityTransformer,
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
from bioetl.application.pipelines.chembl.document_transformer import (
    DocumentTransformer,
)
from bioetl.application.pipelines.chembl.molecule_transformer import (
    MoleculeTransformer,
)
from bioetl.application.pipelines.chembl.target_component_transformer import (
    TargetComponentTransformer,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer

# Deprecated pipeline classes (for backward compatibility)
from bioetl.application.pipelines.compat import (
    ChEMBLActivityPipeline,
    ChEMBLAssayPipeline,
    ChEMBLCellLinePipeline,
    ChEMBLCompoundRecordPipeline,
    ChEMBLDocumentPipeline,
    ChEMBLMoleculePipeline,
    ChEMBLTargetComponentPipeline,
    ChEMBLTargetPipeline,
)

__all__ = [
    "ActivityTransformer",
    "AssayTransformer",
    "BaseChemblTransformer",
    "CellLineTransformer",
    "ChEMBLActivityPipeline",
    "ChEMBLAssayPipeline",
    "ChEMBLCellLinePipeline",
    "ChEMBLCompoundRecordPipeline",
    "ChEMBLDocumentPipeline",
    "ChEMBLMoleculePipeline",
    "ChEMBLTargetComponentPipeline",
    "ChEMBLTargetPipeline",
    "CompoundRecordTransformer",
    "DocumentTransformer",
    "MoleculeTransformer",
    "TargetComponentTransformer",
    "TargetTransformer",
]
