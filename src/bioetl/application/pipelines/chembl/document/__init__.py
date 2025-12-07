"""Stage descriptors wiring for the ChEMBL document pipeline."""

from bioetl.application.pipelines.chembl.document.extract import (
    get_stage_descriptor as get_extract_stage_descriptor,
)
from bioetl.application.pipelines.chembl.document.export import (
    get_stage_descriptor as get_export_stage_descriptor,
)
from bioetl.application.pipelines.chembl.document.transform import (
    get_stage_descriptor as get_transform_stage_descriptor,
)
from bioetl.application.pipelines.chembl.document.validate import (
    get_stage_descriptor as get_validate_stage_descriptor,
)

__all__ = [
    "get_extract_stage_descriptor",
    "get_transform_stage_descriptor",
    "get_validate_stage_descriptor",
    "get_export_stage_descriptor",
]

