from typing import Any

import pandas as pd

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.application.pipelines.chembl.target.extract import extract_target
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.transform.impl.normalize import (
    normalize_chembl_id,
    normalize_uniprot_id,
)


def _normalize_target_components(value: Any) -> Any:
    if not value:
        return None
    if not isinstance(value, list):
        return value

    normalized = []
    for component in value:
        if not isinstance(component, dict):
            continue

        updated = component.copy()
        updated_accession = normalize_uniprot_id(updated.get("accession"))
        if updated_accession:
            updated["accession"] = updated_accession
        normalized.append(updated)

    return normalized if normalized else None


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

        xref_id = updated.get("xref_id")
        if src.lower() == "uniprot":
            normalized_id = normalize_uniprot_id(xref_id)
            updated["xref_id"] = normalized_id if normalized_id else updated.get("xref_id")

        normalized.append(updated)

    return normalized if normalized else None


def _extract_uniprot_id(components: Any, cross_references: Any) -> str | None:
    if isinstance(components, list):
        for component in components:
            if isinstance(component, dict):
                acc = normalize_uniprot_id(component.get("accession"))
                if acc:
                    return acc

    if isinstance(cross_references, list):
        for ref in cross_references:
            if not isinstance(ref, dict):
                continue
            if str(ref.get("xref_src", "")).lower() == "uniprot":
                acc = normalize_uniprot_id(ref.get("xref_id"))
                if acc:
                    return acc

    return None


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

        if "target_chembl_id" in df.columns:
            df["target_chembl_id"] = df["target_chembl_id"].apply(normalize_chembl_id)

        # Map columns if CSV names differ
        if "target_names" in df.columns and "pref_name" not in df.columns:
            df["pref_name"] = df["target_names"]

        if "primaryAccession" in df.columns and "accession" not in df.columns:
            df["accession"] = df["primaryAccession"] # Not in schema but useful?

        # Defaults
        if "target_type" not in df.columns:
            df["target_type"] = "SINGLE PROTEIN" # Default guess

        if "tax_id" in df.columns:
            df["tax_id"] = pd.to_numeric(df["tax_id"], errors="coerce").astype("Int64")

        if "target_components" in df.columns:
            df["target_components"] = df["target_components"].apply(
                _normalize_target_components
            )

        if "cross_references" in df.columns:
            df["cross_references"] = df["cross_references"].apply(
                _normalize_cross_references
            )

        df["uniprot_id"] = df.apply(
            lambda row: _extract_uniprot_id(
                row.get("target_components"), row.get("cross_references")
            ),
            axis=1,
        )
            
        # Filter/Fill schema columns
        schema_columns = list(TargetSchema.to_schema().columns.keys())
        for col in schema_columns:
            if col not in df.columns:
                df[col] = None

        df = df[schema_columns]
        return df
