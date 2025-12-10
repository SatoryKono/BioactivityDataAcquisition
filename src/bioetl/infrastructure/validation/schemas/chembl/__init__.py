"""ChEMBL-specific Pandera schema implementations.

This module provides Pandera DataFrameModel schemas for validating
ChEMBL data tables (activity, assay, cell, molecule, publication,
target, tissue).

All schemas inherit from BaseGeneratedColumnsModel to include
standard service columns (hash_row, hash_business_key, index,
database_version, acquisition_timestamp).
"""

from bioetl.infrastructure.validation.schemas.chembl.activity import (
    ActivityTableSchema,
    OUTPUT_COLUMN_ORDER as ACTIVITY_OUTPUT_COLUMNS,
)
from bioetl.infrastructure.validation.schemas.chembl.assay import (
    AssayTableSchema,
    OUTPUT_COLUMN_ORDER as ASSAY_OUTPUT_COLUMNS,
)
from bioetl.infrastructure.validation.schemas.chembl.cell import (
    CellTableSchema,
    OUTPUT_COLUMN_ORDER as CELL_OUTPUT_COLUMNS,
)
from bioetl.infrastructure.validation.schemas.chembl.molecule import (
    MoleculeTableSchema,
    OUTPUT_COLUMN_ORDER as MOLECULE_OUTPUT_COLUMNS,
)
from bioetl.infrastructure.validation.schemas.chembl.publication import (
    PublicationTableSchema,
    OUTPUT_COLUMN_ORDER as PUBLICATION_OUTPUT_COLUMNS,
)
from bioetl.infrastructure.validation.schemas.chembl.target import (
    TargetTableSchema,
    OUTPUT_COLUMN_ORDER as TARGET_OUTPUT_COLUMNS,
)
from bioetl.infrastructure.validation.schemas.chembl.tissue import (
    TissueTableSchema,
    OUTPUT_COLUMN_ORDER as TISSUE_OUTPUT_COLUMNS,
)

__all__ = [
    # Schema classes
    "ActivityTableSchema",
    "AssayTableSchema",
    "CellTableSchema",
    "MoleculeTableSchema",
    "PublicationTableSchema",
    "TargetTableSchema",
    "TissueTableSchema",
    # Column orders
    "ACTIVITY_OUTPUT_COLUMNS",
    "ASSAY_OUTPUT_COLUMNS",
    "CELL_OUTPUT_COLUMNS",
    "MOLECULE_OUTPUT_COLUMNS",
    "PUBLICATION_OUTPUT_COLUMNS",
    "TARGET_OUTPUT_COLUMNS",
    "TISSUE_OUTPUT_COLUMNS",
]
