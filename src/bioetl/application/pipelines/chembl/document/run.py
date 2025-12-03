import pandas as pd

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.domain.transform.normalizers import normalize_doi, normalize_pmid


class ChemblDocumentPipeline(ChemblPipelineBase):
    """Document pipeline: extraction of document/publication data."""

    ID_COLUMN = "document_chembl_id"
    API_FILTER_KEY = "document_chembl_id__in"

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform document data with proper type conversions."""
        df = df.copy()

        # Map columns
        if "DOI" in df.columns and "doi" not in df.columns:
            df["doi"] = df["DOI"]

        if "doi" in df.columns:
            df["doi_clean"] = df["doi"].apply(normalize_doi)
            df["doi"] = df["doi_clean"]
        else:
            df["doi_clean"] = None

        if "doc_type" not in df.columns:
            df["doc_type"] = "PUBLICATION"

        # Extract chembl_release value from nested dict
        if "chembl_release" in df.columns:
            df["chembl_release"] = df["chembl_release"].apply(
                lambda x: x.get("chembl_release") if isinstance(x, dict) else x
            )

        # Convert nullable integer columns
        for col in ["year", "src_id"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
                df[col] = df[col].astype("Int64")

        # Convert pubmed_id to nullable integer
        if "pubmed_id" in df.columns:
            df["pubmed_id"] = df["pubmed_id"].apply(normalize_pmid)
            df["pubmed_id"] = df["pubmed_id"].astype("Int64")

        return self._enforce_schema(df)
