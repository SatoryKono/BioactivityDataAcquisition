"""
ChEMBL specific schemas.
"""
from bioetl.schemas.chembl.activity import ActivitySchema
from bioetl.schemas.chembl.assay import AssaySchema
from bioetl.schemas.chembl.document import DocumentSchema
from bioetl.schemas.chembl.target import TargetSchema
from bioetl.schemas.chembl.testitem import TestitemSchema

__all__ = [
    "ActivitySchema",
    "AssaySchema",
    "DocumentSchema",
    "TargetSchema",
    "TestitemSchema",
]
