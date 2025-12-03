import pandas as pd

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase


class ChemblTargetPipeline(ChemblPipelineBase):
    """Target pipeline implementation."""

    ID_COLUMN = "target_chembl_id"
    API_FILTER_KEY = "target_chembl_id__in"

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform target data."""
        df = df.copy()

        # Map columns if CSV names differ
        if "target_names" in df.columns and "pref_name" not in df.columns:
            df["pref_name"] = df["target_names"]
        if "primaryAccession" in df.columns and "accession" not in df.columns:
            df["accession"] = df["primaryAccession"]

        # Defaults
        if "target_type" not in df.columns:
            df["target_type"] = "SINGLE PROTEIN"
        if "uniprot_id" not in df.columns:
            df["uniprot_id"] = None

        if "tax_id" in df.columns:
            df["tax_id"] = pd.to_numeric(
                df["tax_id"], errors="coerce"
            ).astype("Int64")

        return df
