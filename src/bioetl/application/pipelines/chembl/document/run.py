import pandas as pd

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase


class ChemblDocumentPipeline(ChemblPipelineBase):
    """Document pipeline: extraction of document/publication data."""

    ID_COLUMN = "document_chembl_id"
    API_FILTER_KEY = "document_chembl_id__in"

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform document data with proper type conversions."""
        df = df.copy()

        # Map columns if CSV names differ
        if "DOI" in df.columns and "doi" not in df.columns:
            df["doi"] = df["DOI"]

        # Default for required field
        if "doc_type" not in df.columns:
            df["doc_type"] = "PUBLICATION"

        # Extract chembl_release value from nested dict
        if "chembl_release" in df.columns:
            df["chembl_release"] = df["chembl_release"].apply(
                lambda x: x.get("chembl_release") if isinstance(x, dict) else x
            )

        # Convert nullable integer columns (Pandera coerce handles basic types,
        # but nullable Int64 needs explicit conversion)
        for col in ["year", "src_id", "pubmed_id"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                df[col] = df[col].astype("Int64")

        return df
