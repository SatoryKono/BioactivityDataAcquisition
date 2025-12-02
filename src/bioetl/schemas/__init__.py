"""
Pandera Schemas.
"""

from bioetl.schemas.registry import registry
from bioetl.schemas.chembl.activity import ActivitySchema
from bioetl.schemas.chembl.assay import AssaySchema
from bioetl.schemas.chembl.document import DocumentSchema
from bioetl.schemas.chembl.target import TargetSchema
from bioetl.schemas.chembl.testitem import TestitemSchema

# Register schemas
registry.register("activity", ActivitySchema)
registry.register("assay", AssaySchema)
registry.register("document", DocumentSchema)
registry.register("target", TargetSchema)
registry.register("testitem", TestitemSchema)
