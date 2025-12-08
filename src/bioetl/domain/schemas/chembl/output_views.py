"""Output column descriptors for ChEMBL schemas."""

from __future__ import annotations

from typing import Type

import pandera.pandas as pa

from bioetl.domain.schemas.chembl.activity import ActivityTableSchema
from bioetl.domain.schemas.chembl.assay import AssayTableSchema
from bioetl.domain.schemas.chembl.base import GENERATED_COLUMN_ORDER
from bioetl.domain.schemas.chembl.cell import CellTableSchema
from bioetl.domain.schemas.chembl.molecule import MoleculeTableSchema
from bioetl.domain.schemas.chembl.publication import PublicationTableSchema
from bioetl.domain.schemas.chembl.target import TargetTableSchema
from bioetl.domain.schemas.chembl.tissue import TissueTableSchema


def _metadata_last(schema_cls: Type[pa.DataFrameModel]) -> list[str]:
    columns = list(schema_cls.to_schema().columns.keys())
    ordered = [col for col in columns if col not in GENERATED_COLUMN_ORDER]
    ordered.extend(col for col in GENERATED_COLUMN_ORDER if col in columns)
    return ordered


ACTIVITY_OUTPUT_COLUMNS = _metadata_last(ActivityTableSchema)
ASSAY_OUTPUT_COLUMNS = _metadata_last(AssayTableSchema)
CELL_OUTPUT_COLUMNS = _metadata_last(CellTableSchema)
MOLECULE_OUTPUT_COLUMNS = _metadata_last(MoleculeTableSchema)
PUBLICATION_OUTPUT_COLUMNS = _metadata_last(PublicationTableSchema)
TARGET_OUTPUT_COLUMNS = _metadata_last(TargetTableSchema)
TISSUE_OUTPUT_COLUMNS = _metadata_last(TissueTableSchema)

__all__ = [
    "ACTIVITY_OUTPUT_COLUMNS",
    "ASSAY_OUTPUT_COLUMNS",
    "CELL_OUTPUT_COLUMNS",
    "MOLECULE_OUTPUT_COLUMNS",
    "PUBLICATION_OUTPUT_COLUMNS",
    "TARGET_OUTPUT_COLUMNS",
    "TISSUE_OUTPUT_COLUMNS",
]
