"""
Common input helpers for ChEMBL pipelines.
"""
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from bioetl.infrastructure.config.models import PipelineConfig

logger = logging.getLogger(__name__)


def _get_input_path(config: PipelineConfig) -> Path | None:
    """Get input file path from config."""
    input_file = config.cli.get("input_file")
    if not input_file:
        return None
    return Path(input_file)


def read_input_ids(config: PipelineConfig, id_col: str) -> list[str] | None:
    """
    Read list of IDs from input CSV file if specified in config.
    
    Args:
        config: Pipeline configuration
        id_col: Column name containing the IDs
        
    Returns:
        List of IDs if input file is specified, None otherwise.
        
    Raises:
        ValueError: If input file is specified but does not exist or is missing the ID column.
    """
    path = _get_input_path(config)
    if not path:
        return None

    if not path.exists():
        raise ValueError(f"Input file not found: {path}")

    logger.info(f"Reading IDs from {path} using column {id_col}")
    
    # Read only the ID column to verify it exists and get values
    try:
        # First read header to check columns
        header = pd.read_csv(path, nrows=0)
        if id_col not in header.columns:
            # Try to handle cases where maybe the file has no header or different format?
            # For now, strictly enforce column presence.
            raise ValueError(f"Input CSV {path} must contain '{id_col}' column")
        
        # Read full column
        df = pd.read_csv(path, usecols=[id_col])
        ids = df[id_col].dropna().astype(str).tolist()
        logger.info(f"Loaded {len(ids)} IDs from input file")
        return ids
        
    except Exception as e:
        raise ValueError(f"Error reading input file {path}: {e}") from e


def read_input_dataframe(config: PipelineConfig, id_col: str) -> pd.DataFrame | None:
    """
    Read full DataFrame from input CSV file if specified in config.
    
    Args:
        config: Pipeline configuration
        id_col: Column name containing the IDs (for validation)
        
    Returns:
        DataFrame if input file is specified, None otherwise.
        
    Raises:
        ValueError: If input file is specified but does not exist or is missing the ID column.
    """
    path = _get_input_path(config)
    if not path:
        return None

    if not path.exists():
        raise ValueError(f"Input file not found: {path}")

    logger.info(f"Reading DataFrame from {path}")
    
    try:
        df = pd.read_csv(path)
        if id_col not in df.columns:
            raise ValueError(f"Input CSV {path} must contain '{id_col}' column")
        
        logger.info(f"Loaded {len(df)} records from input file")
        return df
        
    except Exception as e:
        raise ValueError(f"Error reading input file {path}: {e}") from e

