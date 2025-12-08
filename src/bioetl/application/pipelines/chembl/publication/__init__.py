"""Stage descriptors wiring for the ChEMBL publication pipeline."""

from bioetl.application.pipelines.chembl.publication.export import (
    get_stage_descriptor as get_export_stage_descriptor,
)
from bioetl.application.pipelines.chembl.publication.extract import (
    get_stage_descriptor as get_extract_stage_descriptor,
)
from bioetl.application.pipelines.chembl.publication.transform import (
    get_stage_descriptor as get_transform_stage_descriptor,
)
from bioetl.application.pipelines.chembl.publication.validate import (
    get_stage_descriptor as get_validate_stage_descriptor,
)

__all__ = [
    "get_extract_stage_descriptor",
    "get_transform_stage_descriptor",
    "get_validate_stage_descriptor",
    "get_export_stage_descriptor",
]
