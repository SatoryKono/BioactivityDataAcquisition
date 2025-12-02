from typing import Any
import pandas as pd
from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.application.pipelines.chembl.activity.extract import extract_activity


class ChemblActivityPipeline(ChemblPipelineBase):
    """
    Activity pipeline implementation.
    """
    
    def extract(self, **kwargs: Any) -> pd.DataFrame:
        """
        Extract activity data, supporting CSV input.
        """
        return extract_activity(self._config, self._extraction_service, **kwargs)
    
    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Drop extra columns that are not in the schema.
        """
        # Get allowed columns from schema
        # ActivitySchema is a DataFrameModel, so we can inspect its fields
        allowed_columns = set(ActivitySchema.to_schema().columns.keys())
        
        # Intersect with dataframe columns to keep only allowed ones
        # We must ensure we don't drop columns that are not yet created (e.g. hash columns are added later?)
        # Wait, hash columns are added in base.py AFTER transform.
        # So we should only keep columns that are in schema OR are intended to be there.
        
        # Actually, validation happens after transform and after hashing.
        # The validation expects hash_row and hash_business_key.
        # These are added in `PipelineBase.run` -> `_add_hash_columns` which happens AFTER `transform`.
        # So at this point (transform), hash columns might NOT be there yet.
        # But `allowed_columns` includes them.
        
        # If I restrict to `allowed_columns`, and `hash_row` is not in `df` yet, it's fine, I just won't select it.
        # But I must make sure I don't select columns that don't exist in `df` (KeyError).
        
        cols_to_keep = [c for c in df.columns if c in allowed_columns]
        
        return df[cols_to_keep]
