"""
ChEMBL specific schemas.
"""
from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.schemas.chembl.document import DocumentSchema
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.chembl.testitem import TestitemSchema
from bioetl.domain.schemas.chembl.models import (
    ActivityModel,
    ChemblRecordModel,
)

__all__ = [
    "ActivitySchema",
    "AssaySchema",
    "DocumentSchema",
    "TargetSchema",
    "TestitemSchema",
    "ActivityModel",
    "ChemblRecordModel",
]
