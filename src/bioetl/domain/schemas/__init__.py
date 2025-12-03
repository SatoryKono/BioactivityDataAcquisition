"""
Pandera Schemas.
"""

from bioetl.domain.schemas.chembl.activity import (
    ActivityOutputSchema,
    ActivitySchema,
)
from bioetl.domain.schemas.chembl.assay import AssayOutputSchema, AssaySchema
from bioetl.domain.schemas.chembl.document import (
    DocumentOutputSchema,
    DocumentSchema,
)
from bioetl.domain.schemas.chembl.target import TargetOutputSchema, TargetSchema
from bioetl.domain.schemas.chembl.testitem import TestitemOutputSchema, TestitemSchema
from bioetl.domain.validation.contracts import SchemaProviderABC


def register_schemas(registry: SchemaProviderABC) -> None:
    """Register all schemas to the provided registry."""
    registry.register("activity", ActivitySchema)
    registry.register_output_descriptor("activity", ActivityOutputSchema)
    registry.register("assay", AssaySchema)
    registry.register_output_descriptor("assay", AssayOutputSchema)
    registry.register("document", DocumentSchema)
    registry.register_output_descriptor("document", DocumentOutputSchema)
    registry.register("target", TargetSchema)
    registry.register_output_descriptor("target", TargetOutputSchema)
    registry.register("testitem", TestitemSchema)
    registry.register_output_descriptor("testitem", TestitemOutputSchema)
