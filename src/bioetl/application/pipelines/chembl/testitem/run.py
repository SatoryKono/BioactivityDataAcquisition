from typing import Any

import pandas as pd

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.application.pipelines.chembl.testitem.extract import extract_testitem
from bioetl.domain.schemas.chembl.testitem import TestitemSchema
from bioetl.domain.transform.custom_types import (
    normalize_chembl_id,
    normalize_pcid,
)
from bioetl.infrastructure.config.source_chembl import ChemblSourceConfig


def _normalize_cross_references(value: Any) -> Any:
    if not value:
        return None
    if not isinstance(value, list):
        return value

    normalized = []
    for ref in value:
        if not isinstance(ref, dict):
            continue

        updated = ref.copy()
        src = str(updated.get("xref_src", "")).strip()
        updated["xref_src"] = src if src else None

        if src.lower() == "pubchem":
            cid = normalize_pcid(updated.get("xref_id"))
            if cid:
                updated["xref_id"] = cid

        normalized.append(updated)

    return normalized if normalized else None


def _extract_pubchem_cid(row: pd.Series) -> int | None:
    cid_direct = normalize_pcid(row.get("pubchem_cid"))
    if cid_direct:
        return cid_direct

    cross_references = row.get("cross_references")
    if isinstance(cross_references, list):
        for ref in cross_references:
            if not isinstance(ref, dict):
                continue
            if str(ref.get("xref_src", "")).lower() == "pubchem":
                cid = normalize_pcid(ref.get("xref_id"))
                if cid:
                    return cid

    return None


class ChemblTestitemPipeline(ChemblPipelineBase):
    """
    TestItem pipeline: извлекает данные молекул из ChEMBL /molecule endpoint.
    Трансформирует в формат testitem согласно схеме.
    """

    # Колонки для выходного датасета (from old code, but schema is authority)
    # We should use schema fields.

    def _resolve_source_config(self, source_name: str) -> ChemblSourceConfig:
        """
        Resolves and validates source configuration.
        """
        source_data = self._config.sources.get(source_name)
        
        if isinstance(source_data, ChemblSourceConfig):
            return source_data
            
        if isinstance(source_data, dict):
            return ChemblSourceConfig(**source_data)
            
        raise ValueError(f"Configuration for source '{source_name}' is missing or invalid.")
    
    def extract(self, **kwargs: Any) -> pd.DataFrame:
        """
        Extract testitem data, supporting CSV input.
        """
        source_config = self._resolve_source_config("chembl")
        batch_size = source_config.resolve_effective_batch_size()

        return extract_testitem(
            self._config, 
            self._extraction_service,
            batch_size=batch_size,
            **kwargs
        )

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Трансформация данных molecule в testitem формат.
        """
        df = df.copy()

        if "molecule_chembl_id" in df.columns:
            df["molecule_chembl_id"] = df["molecule_chembl_id"].apply(
                normalize_chembl_id
            )
        
        # Map columns
        # CSV has 'canonical_smiles', Schema has 'molecule_structures' dict?
        # Or 'structure_type'?
        # TestitemSchema has 'molecule_structures'.
        # If we have 'canonical_smiles' in CSV, we should probably pack it into 'molecule_structures' dict
        # OR the schema expects flattened fields? No, schema has `molecule_structures: Series[object]`.
        
        if "molecule_structures" not in df.columns and "canonical_smiles" in df.columns:
            # Pack into dict
            df["molecule_structures"] = df["canonical_smiles"].apply(
                lambda x: {"canonical_smiles": x} if pd.notna(x) else None
            )
             
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

        if "cross_references" in df.columns:
            df["cross_references"] = df["cross_references"].apply(
                _normalize_cross_references
            )

        df["pubchem_cid"] = df.apply(_extract_pubchem_cid, axis=1)

        # Schema enforcement
        schema_columns = list(TestitemSchema.to_schema().columns.keys())
        for col in schema_columns:
            if col not in df.columns:
                df[col] = None

        df = df[schema_columns]

        return df
