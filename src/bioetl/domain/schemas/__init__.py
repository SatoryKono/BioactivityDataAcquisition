"""
Pandera Schemas.
"""

from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.schemas.chembl.document import DocumentSchema
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.chembl.testitem import TestitemSchema
from bioetl.domain.schemas.chembl.output_views import (
    ACTIVITY_OUTPUT_COLUMNS,
    ASSAY_OUTPUT_COLUMNS,
    DOCUMENT_OUTPUT_COLUMNS,
    TARGET_OUTPUT_COLUMNS,
    TESTITEM_OUTPUT_COLUMNS,
)
from bioetl.domain.validation.contracts import SchemaProviderABC


def register_schemas(registry: SchemaProviderABC) -> None:
    """Register all schemas to the provided registry."""
    registry.register("activity", ActivitySchema)
    registry.register("activity_input", ActivitySchema)
    registry.register(
        "activity_output", ActivitySchema, column_order=ACTIVITY_OUTPUT_COLUMNS
    )
    registry.register("assay", AssaySchema)
    registry.register("assay_input", AssaySchema)
    registry.register("assay_output", AssaySchema, column_order=ASSAY_OUTPUT_COLUMNS)
    registry.register("document", DocumentSchema)
    registry.register("document_input", DocumentSchema)
    registry.register(
        "document_output", DocumentSchema, column_order=DOCUMENT_OUTPUT_COLUMNS
    )
    registry.register("target", TargetSchema)
    registry.register("target_input", TargetSchema)
    registry.register("target_output", TargetSchema, column_order=TARGET_OUTPUT_COLUMNS)
    registry.register("testitem", TestitemSchema)
    registry.register("testitem_input", TestitemSchema)
    registry.register(
        "testitem_output", TestitemSchema, column_order=TESTITEM_OUTPUT_COLUMNS
    )
