"""
Extraction logic for Activity pipeline.
"""
import logging
from typing import Any

import pandas as pd

from bioetl.application.pipelines.chembl.common.inputs import read_input_dataframe, read_input_ids
from bioetl.application.pipelines.chembl.extraction import ChemblExtractionService
from bioetl.infrastructure.config.models import PipelineConfig
from bioetl.infrastructure.config.source_chembl import ChemblSourceConfig
from bioetl.infrastructure.clients.chembl.response_parser import ChemblResponseParser

logger = logging.getLogger(__name__)


def _chunk_list(data: list[Any], size: int):
    """Yield successive chunks from data."""
    for i in range(0, len(data), size):
        yield data[i:i + size]


def extract_activity(
    config: PipelineConfig,
    service: ChemblExtractionService,
    **kwargs: Any
) -> pd.DataFrame:
    """Extract activity data with optional CSV input handling.

    When ``config.cli['input_file']`` is provided, the file must contain an
    ``activity_id`` column or a :class:`ValueError` is raised. If the CSV only
    contains IDs (``activity_id`` plus at most one more column), the function
    fetches full records from the ChEMBL API for those IDs; if the CSV already
    includes full data, the dataframe is returned as-is. The optional
    ``limit`` keyword truncates either the loaded dataframe (full CSV) or the
    list of IDs (ID-only CSV) before further processing. Without ``input_file``
    the function delegates to :meth:`ChemblExtractionService.extract_all` for
    the ``activity`` entity.
    """
    # Resolve source config for batch sizing
    source_raw = config.sources.get("chembl", {})
    # If it's already an object (e.g. resolver did it), use it, otherwise parse dict
    if isinstance(source_raw, ChemblSourceConfig):
        source_config = source_raw
    else:
        source_config = ChemblSourceConfig.model_validate(source_raw)

    limit = kwargs.get("limit")
    
    path = config.cli.get("input_file")
    if path:
        header = pd.read_csv(path, nrows=0)
        if "activity_id" not in header.columns:
             raise ValueError(f"Input file {path} must contain 'activity_id'")
             
        is_id_only = len(header.columns) <= 2 and "activity_id" in header.columns
        
        if not is_id_only:
            logger.info("Detected full data in input CSV.")
            df = read_input_dataframe(config, id_col="activity_id")
            if df is None:
                return pd.DataFrame()

            if limit:
                logger.info(f"Applying limit {limit} to input DataFrame")
                df = df.head(limit)
            return df
        
        logger.info("Detected ID-only input CSV. Fetching data from API...")
        ids = read_input_ids(config, id_col="activity_id")
        if not ids:
            return pd.DataFrame()

        if limit:
            logger.info(f"Applying limit {limit} to input IDs")
            ids = ids[:limit]

        records = []
        # Calculate batch size dynamically based on config and limit
        batch_size = source_config.resolve_effective_batch_size(limit=limit, hard_cap=25)
        
        parser = ChemblResponseParser()
        
        for batch_ids in _chunk_list(ids, batch_size):
            batch_ids_typed = [int(x) for x in batch_ids if str(x).isdigit()]
            if not batch_ids_typed:
                continue
            
            str_ids = ",".join(map(str, batch_ids_typed))
            response = service.client.request_activity(activity_id__in=str_ids)
            batch_records = parser.parse(response)
            records.extend(batch_records)
            
        return pd.DataFrame(records)

    return service.extract_all("activity", **kwargs)
