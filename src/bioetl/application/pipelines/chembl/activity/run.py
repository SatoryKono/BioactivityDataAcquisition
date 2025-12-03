"""ChEMBL Activity pipeline implementation."""
import pandas as pd

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase


class ChemblActivityPipeline(ChemblPipelineBase):
    """Activity pipeline implementation."""

    ID_COLUMN = "activity_id"
    API_FILTER_KEY = "activity_id__in"

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enforce schema columns."""
        return self._enforce_schema(df)
