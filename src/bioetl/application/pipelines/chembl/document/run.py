import pandas as pd

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase


class ChemblDocumentPipeline(ChemblPipelineBase):
    """
    Document pipeline implementation.
    
    Handles extraction of document/publication data from ChEMBL API.
    """

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform document data with proper type conversions.
        
        - Extracts chembl_release string from nested object
        - Converts nullable integer columns to pandas Int64 dtype
        - Converts pubmed_id to string (for consistency with other IDs)
        """
        df = df.copy()
        
        # Extract chembl_release value from nested dict
        if "chembl_release" in df.columns:
            df["chembl_release"] = df["chembl_release"].apply(
                lambda x: x.get("chembl_release") if isinstance(x, dict) else x
            )
        
        # Convert nullable integer columns to Int64 (pandas nullable integer)
        int_columns = ["year", "src_id"]
        for col in int_columns:
            if col in df.columns:
                df[col] = df[col].astype("Int64")
        
        # Convert pubmed_id to string (nullable)
        if "pubmed_id" in df.columns:
            df["pubmed_id"] = df["pubmed_id"].astype("Int64").astype("string")
        
        return df
