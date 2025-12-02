from typing import Any
import pandas as pd
from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.application.pipelines.chembl.assay.extract import extract_assay
from bioetl.domain.schemas.chembl.assay import AssaySchema


class ChemblAssayPipeline(ChemblPipelineBase):
    """
    Assay pipeline implementation.
    """
    
    def extract(self, **kwargs: Any) -> pd.DataFrame:
        """
        Extract assay data, supporting CSV input.
        """
        return extract_assay(self._config, self._extraction_service, **kwargs)

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform assay data.
        Fill missing required columns with defaults for CSV compatibility.
        """
        df = df.copy()
        
        # Defaults for required fields missing in CSV
        if "assay_type" not in df.columns:
            # If 'Target TYPE' exists, maybe we can use it? No, it's target type.
            # Default to "U" (Unspecified) if allowed, or "B" (Binding)
            df["assay_type"] = "U"
            
        if "assay_category" not in df.columns:
            df["assay_category"] = "unknown"
            
        if "confidence_score" not in df.columns:
            df["confidence_score"] = 0
            
        # Filter to schema columns
        allowed_columns = set(AssaySchema.to_schema().columns.keys())
        
        # Add any other missing nullable columns as None
        for col in allowed_columns:
            if col not in df.columns:
                df[col] = None
                
        # Select only allowed columns
        df = df[[c for c in df.columns if c in allowed_columns]]
        
        return df
