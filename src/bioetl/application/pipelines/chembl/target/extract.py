"""
Extraction logic for Target pipeline.
"""
import logging
from typing import Any

import pandas as pd

from bioetl.application.pipelines.chembl.common.inputs import read_input_dataframe, read_input_ids
from bioetl.application.pipelines.chembl.extraction import ChemblExtractionService
from bioetl.infrastructure.config.models import PipelineConfig
from bioetl.infrastructure.clients.chembl.response_parser import ChemblResponseParser

logger = logging.getLogger(__name__)


def _chunk_list(data: list[Any], size: int):
    """Yield successive chunks from data."""
    for i in range(0, len(data), size):
        yield data[i:i + size]


def extract_target(
    config: PipelineConfig, 
    service: ChemblExtractionService, 
    **kwargs: Any
) -> pd.DataFrame:
    """
    Extract target data.
    """
    path = config.cli.get("input_file")
    if path:
        header = pd.read_csv(path, nrows=0)
        if "target_chembl_id" not in header.columns:
             raise ValueError(f"Input file {path} must contain 'target_chembl_id'")
             
        is_id_only = len(header.columns) <= 2 and "target_chembl_id" in header.columns
        limit = kwargs.get("limit")
        
        if not is_id_only:
            logger.info("Detected full data in input CSV.")
            df = read_input_dataframe(config, id_col="target_chembl_id")
            if df is None:
                return pd.DataFrame()

            if limit:
                df = df.head(limit)
            return df
        
        logger.info("Detected ID-only input CSV. Fetching data from API...")
        ids = read_input_ids(config, id_col="target_chembl_id")
        if not ids:
            return pd.DataFrame()
            
        if limit:
            ids = ids[:limit]

        records = []
        batch_size = 100
        parser = ChemblResponseParser()
        
        for batch_ids in _chunk_list(ids, batch_size):
            str_ids = ",".join(map(str, batch_ids))
            response = service.client.request_target(target_chembl_id__in=str_ids)
            batch_records = parser.parse(response)
            records.extend(batch_records)
            
        return pd.DataFrame(records)

    return service.extract_all("target", **kwargs)
