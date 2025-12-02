from typing import Any
import pandas as pd
from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.application.pipelines.chembl.target.extract import extract_target
from bioetl.domain.schemas.chembl.target import TargetSchema


class ChemblTargetPipeline(ChemblPipelineBase):
    """
    Target pipeline implementation.
    """
    
    def extract(self, **kwargs: Any) -> pd.DataFrame:
        """
        Extract target data, supporting CSV input.
        """
        return extract_target(self._config, self._extraction_service, **kwargs)

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform target data.
        """
        df = df.copy()
        
        # Map columns if CSV names differ
        if "target_names" in df.columns and "pref_name" not in df.columns:
            df["pref_name"] = df["target_names"]
            
        if "primaryAccession" in df.columns and "accession" not in df.columns:
             df["accession"] = df["primaryAccession"] # Not in schema but useful?

        # Defaults
        if "target_type" not in df.columns:
            df["target_type"] = "SINGLE PROTEIN" # Default guess
            
        # Filter/Fill schema columns
        allowed_columns = set(TargetSchema.to_schema().columns.keys())
        for col in allowed_columns:
            if col not in df.columns:
                df[col] = None
                
        df = df[[c for c in df.columns if c in allowed_columns]]
        return df
