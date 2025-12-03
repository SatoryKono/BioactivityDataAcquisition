import pandas as pd

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase


class ChemblTestitemPipeline(ChemblPipelineBase):
    """TestItem pipeline: molecules from ChEMBL /molecule endpoint."""

    ID_COLUMN = "molecule_chembl_id"
    API_FILTER_KEY = "molecule_chembl_id__in"

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transform molecule data to testitem format."""
        df = df.copy()

        # Pack canonical_smiles into molecule_structures dict
        if "molecule_structures" not in df.columns and "canonical_smiles" in df.columns:
            df["molecule_structures"] = df["canonical_smiles"].apply(
                lambda x: {"canonical_smiles": x} if pd.notna(x) else None
            )

        # Defaults
        if "structure_type" not in df.columns:
            df["structure_type"] = "MOL"
        if "pubchem_cid" not in df.columns:
            df["pubchem_cid"] = None

        if "all_names" in df.columns and "pref_name" not in df.columns:
            df["pref_name"] = df["all_names"].astype(str).apply(
                lambda x: x.split(",")[0] if x else None
            )

        if "max_phase" in df.columns:
            df["max_phase"] = pd.to_numeric(
                df["max_phase"], errors="coerce"
            ).astype("Int64")

        return self._enforce_schema(df)
