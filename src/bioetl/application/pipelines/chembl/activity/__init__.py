"""Stage descriptors wiring for the ChEMBL activity pipeline."""

from bioetl.application.pipelines.chembl.activity.extract import (
    get_stage_descriptor as get_extract_stage_descriptor,
)
from bioetl.application.pipelines.chembl.activity.export import (
    get_stage_descriptor as get_export_stage_descriptor,
)
from bioetl.application.pipelines.chembl.activity.transform import (
    get_stage_descriptor as get_transform_stage_descriptor,
)
from bioetl.application.pipelines.chembl.activity.validate import (
    get_stage_descriptor as get_validate_stage_descriptor,
)

__all__ = [
    "get_extract_stage_descriptor",
    "get_transform_stage_descriptor",
    "get_validate_stage_descriptor",
    "get_export_stage_descriptor",
]

