"""Output column descriptors for ChEMBL schemas."""

from __future__ import annotations

from typing import Type

import pandera.pandas as pa

from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.schemas.chembl.document import DocumentSchema
from bioetl.domain.schemas.chembl.molecule import MoleculeSchema
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.chembl.testitem import TestitemSchema

_OUTPUT_METADATA_COLUMNS = [
    "hash_row",
    "hash_business_key",
    "index",
    "database_version",
    "extracted_at",
]


def _metadata_last(schema_cls: Type[pa.DataFrameModel]) -> list[str]:
    columns = list(schema_cls.to_schema().columns.keys())
    ordered = [col for col in columns if col not in _OUTPUT_METADATA_COLUMNS]
    ordered.extend(col for col in _OUTPUT_METADATA_COLUMNS if col in columns)
    return ordered


ACTIVITY_OUTPUT_COLUMNS = _metadata_last(ActivitySchema)
ASSAY_OUTPUT_COLUMNS = _metadata_last(AssaySchema)
DOCUMENT_OUTPUT_COLUMNS = _metadata_last(DocumentSchema)
MOLECULE_OUTPUT_COLUMNS = _metadata_last(MoleculeSchema)
TARGET_OUTPUT_COLUMNS = _metadata_last(TargetSchema)
TESTITEM_OUTPUT_COLUMNS = _metadata_last(TestitemSchema)

__all__ = [
    "ACTIVITY_OUTPUT_COLUMNS",
    "ASSAY_OUTPUT_COLUMNS",
    "DOCUMENT_OUTPUT_COLUMNS",
    "MOLECULE_OUTPUT_COLUMNS",
    "TARGET_OUTPUT_COLUMNS",
    "TESTITEM_OUTPUT_COLUMNS",
]
