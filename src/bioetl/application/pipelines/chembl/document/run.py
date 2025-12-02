from typing import Any

import pandas as pd

from bioetl.application.pipelines.chembl.base import ChemblPipelineBase
from bioetl.application.pipelines.chembl.document.extract import extract_document
from bioetl.domain.schemas.chembl.document import DocumentSchema
from bioetl.domain.transform.custom_types import normalize_doi, normalize_pmid
from bioetl.infrastructure.config.source_chembl import ChemblSourceConfig


class ChemblDocumentPipeline(ChemblPipelineBase):
    """
    Document pipeline implementation.
    
    Handles extraction of document/publication data from ChEMBL API.
    """

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
        Extract document data, supporting CSV input.
        """
        source_config = self._resolve_source_config("chembl")
        batch_size = source_config.resolve_effective_batch_size()

        return extract_document(
            self._config, 
            self._extraction_service, 
            batch_size=batch_size, 
            **kwargs
        )

    def _do_transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transform document data with proper type conversions.
        """
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
            # Check if it's dict or string (CSV is string usually, API is dict)
            # If CSV, it might be null or string.
            # API returns dict usually.
            df["chembl_release"] = df["chembl_release"].apply(
                lambda x: x.get("chembl_release") if isinstance(x, dict) else x
            )
        
        # Convert nullable integer columns to Int64 (pandas nullable integer)
        int_columns = ["year", "src_id"]
        for col in int_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").astype("Int64")

        # Convert pubmed_id to nullable integer
        if "pubmed_id" in df.columns:
            df["pubmed_id"] = df["pubmed_id"].apply(normalize_pmid)
            df["pubmed_id"] = df["pubmed_id"].astype("Int64")

        # Schema enforcement
        schema_columns = list(DocumentSchema.to_schema().columns.keys())
        for col in schema_columns:
            if col not in df.columns:
                df[col] = None

        df = df[schema_columns]

        return df
