import pandas as pd

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase


class ChemblAssayPipeline(ChemblPipelineBase):
    """Assay pipeline implementation."""

    ID_COLUMN = "assay_chembl_id"
    API_FILTER_KEY = "assay_chembl_id__in"

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform assay data with defaults for CSV compatibility."""
        df = df.copy()

        # Defaults for required fields missing in CSV
        if "assay_type" not in df.columns:
            df["assay_type"] = "U"
        if "assay_category" not in df.columns:
            df["assay_category"] = "unknown"
        if "confidence_score" not in df.columns:
            df["confidence_score"] = 0

        return self._enforce_schema(df)
