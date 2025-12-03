"""ChEMBL Activity pipeline implementation."""
from bioetl.application.pipelines.chembl.base import ChemblPipelineBase


class ChemblActivityPipeline(ChemblPipelineBase):
    """Activity pipeline implementation."""

    ID_COLUMN = "activity_id"
    API_FILTER_KEY = "activity_id__in"

    # No custom _do_transform needed - base class handles everything
