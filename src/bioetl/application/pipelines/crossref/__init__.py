"""CrossRef pipeline components.

Transformers and utilities for CrossRef data processing.
"""

from bioetl.application.pipelines.crossref.transformer import (
    CrossRefPublicationTransformer,
)

__all__ = ["CrossRefPublicationTransformer"]
