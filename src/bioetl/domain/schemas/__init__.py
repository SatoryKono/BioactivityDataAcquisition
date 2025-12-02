"""
Pandera Schemas.
"""

from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.schemas.chembl.document import DocumentSchema
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.chembl.testitem import TestitemSchema
from bioetl.domain.validation.contracts import SchemaProviderABC


def register_schemas(registry: SchemaProviderABC) -> None:
    """Register all schemas to the provided registry."""
    registry.register("activity", ActivitySchema)
    registry.register("assay", AssaySchema)
    registry.register("document", DocumentSchema)
    registry.register("target", TargetSchema)
    registry.register("testitem", TestitemSchema)
