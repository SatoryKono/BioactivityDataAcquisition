"""
Pandera Schemas.
"""

from bioetl.domain.schemas.chembl.activity import ActivityTableSchema
from bioetl.domain.schemas.chembl.assay import AssayTableSchema
from bioetl.domain.schemas.chembl.cell import CellTableSchema
from bioetl.domain.schemas.chembl.document import DocumentTableSchema
from bioetl.domain.schemas.chembl.molecule import MoleculeTableSchema
from bioetl.domain.schemas.chembl.output_views import (
    ACTIVITY_OUTPUT_COLUMNS,
    ASSAY_OUTPUT_COLUMNS,
    CELL_OUTPUT_COLUMNS,
    DOCUMENT_OUTPUT_COLUMNS,
    MOLECULE_OUTPUT_COLUMNS,
    TARGET_OUTPUT_COLUMNS,
    TISSUE_OUTPUT_COLUMNS,
)
from bioetl.domain.schemas.chembl.target import TargetTableSchema
from bioetl.domain.schemas.chembl.tissue import TissueTableSchema
from bioetl.domain.validation.contracts import SchemaProviderABC


def register_schemas(registry: SchemaProviderABC) -> None:
    """Register all schemas to the provided registry."""
    registry.register("activity", ActivityTableSchema)
    registry.register("activity_input", ActivityTableSchema)
    registry.register(
        "activity_output", ActivityTableSchema, column_order=ACTIVITY_OUTPUT_COLUMNS
    )
    registry.register("assay", AssayTableSchema)
    registry.register("assay_input", AssayTableSchema)
    registry.register(
        "assay_output", AssayTableSchema, column_order=ASSAY_OUTPUT_COLUMNS
    )
    registry.register("document", DocumentTableSchema)
    registry.register("document_input", DocumentTableSchema)
    registry.register(
        "document_output", DocumentTableSchema, column_order=DOCUMENT_OUTPUT_COLUMNS
    )
    registry.register("cell", CellTableSchema)
    registry.register("cell_input", CellTableSchema)
    registry.register(
        "cell_output", CellTableSchema, column_order=CELL_OUTPUT_COLUMNS
    )
    registry.register("molecule", MoleculeTableSchema)
    registry.register("molecule_input", MoleculeTableSchema)
    registry.register(
        "molecule_output", MoleculeTableSchema, column_order=MOLECULE_OUTPUT_COLUMNS
    )
    registry.register("target", TargetTableSchema)
    registry.register("target_input", TargetTableSchema)
    registry.register(
        "target_output", TargetTableSchema, column_order=TARGET_OUTPUT_COLUMNS
    )
    registry.register("tissue", TissueTableSchema)
    registry.register("tissue_input", TissueTableSchema)
    registry.register(
        "tissue_output", TissueTableSchema, column_order=TISSUE_OUTPUT_COLUMNS
    )
