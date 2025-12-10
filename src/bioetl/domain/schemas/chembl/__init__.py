"""ChEMBL specific schemas.

.. deprecated::
    This module re-exports Pandera schemas from infrastructure for
    backward compatibility. New code should import directly from:
    - ``bioetl.infrastructure.validation.schemas.chembl``
    - ``bioetl.infrastructure.validation.schemas.pandera_base``

    Domain field specifications are available in:
    - ``bioetl.domain.schemas.field_specs``
"""

import warnings

# Re-export from infrastructure layer for backward compatibility
from bioetl.infrastructure.validation.schemas.pandera_base import (
    GENERATED_COLUMN_ORDER,
    BaseGeneratedColumnsModel,
    BaseGeneratedColumnsSchema,
    build_output_column_order,
)
from bioetl.infrastructure.validation.schemas.chembl.activity import ActivityTableSchema
from bioetl.infrastructure.validation.schemas.chembl.assay import AssayTableSchema
from bioetl.infrastructure.validation.schemas.chembl.cell import CellTableSchema
from bioetl.infrastructure.validation.schemas.chembl.molecule import MoleculeTableSchema
from bioetl.infrastructure.validation.schemas.chembl.publication import (
    PublicationTableSchema,
)
from bioetl.infrastructure.validation.schemas.chembl.target import TargetTableSchema
from bioetl.infrastructure.validation.schemas.chembl.tissue import TissueTableSchema


def __getattr__(name: str) -> object:
    """Emit deprecation warning on first access to module-level names."""
    if name in __all__:
        warnings.warn(
            f"Importing '{name}' from bioetl.domain.schemas.chembl is deprecated. "
            f"Import from bioetl.infrastructure.validation.schemas.chembl instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return globals()[f"_{name}"] if f"_{name}" in globals() else globals().get(name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "BaseGeneratedColumnsModel",
    "BaseGeneratedColumnsSchema",
    "ActivityTableSchema",
    "AssayTableSchema",
    "CellTableSchema",
    "PublicationTableSchema",
    "MoleculeTableSchema",
    "TargetTableSchema",
    "TissueTableSchema",
    "GENERATED_COLUMN_ORDER",
    "build_output_column_order",
]
