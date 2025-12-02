from typing import Any

import pandas as pd

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.application.pipelines.chembl.testitem.extract import extract_testitem
from bioetl.domain.schemas.chembl.testitem import TestitemSchema


class ChemblTestitemPipeline(ChemblPipelineBase):
    """
    TestItem pipeline: извлекает данные молекул из ChEMBL /molecule endpoint.
    Трансформирует в формат testitem согласно схеме.
    """

    # Колонки для выходного датасета (from old code, but schema is authority)
    # We should use schema fields.
    
    def extract(self, **kwargs: Any) -> pd.DataFrame:
        """
        Extract testitem data, supporting CSV input.
        """
        return extract_testitem(self._config, self._extraction_service, **kwargs)

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Трансформация данных molecule в testitem формат.
        """
        df = df.copy()
        
        # Map columns
        # CSV has 'canonical_smiles', Schema has 'molecule_structures' dict?
        # Or 'structure_type'?
        # TestitemSchema has 'molecule_structures'.
        # If we have 'canonical_smiles' in CSV, we should probably pack it into 'molecule_structures' dict
        # OR the schema expects flattened fields? No, schema has `molecule_structures: Series[object]`.
        
        if "molecule_structures" not in df.columns and "canonical_smiles" in df.columns:
             # Pack into dict
             df["molecule_structures"] = df["canonical_smiles"].apply(lambda x: {"canonical_smiles": x} if pd.notna(x) else None)
             
        if "structure_type" not in df.columns:
            df["structure_type"] = "MOL" # Default
            
        if "all_names" in df.columns and "pref_name" not in df.columns:
            # Use all_names as pref_name (first one?)
            df["pref_name"] = df["all_names"].astype(str).apply(lambda x: x.split(',')[0] if x else None)

        # Приводим max_phase к int, заменяя None на pd.NA
        if "max_phase" in df.columns:
            df["max_phase"] = pd.to_numeric(
                df["max_phase"], errors="coerce"
            ).astype("Int64")

        # Schema enforcement
        allowed_columns = set(TestitemSchema.to_schema().columns.keys())
        for col in allowed_columns:
            if col not in df.columns:
                df[col] = None

        df = df[[c for c in df.columns if c in allowed_columns]]
        
        return df
