"""CrossRef pipeline components.

Transformers and utilities for CrossRef data processing.
"""

from bioetl.application.pipelines.crossref.transformer import (
    CrossRefPublicationTransformer,
)

# Backward compatibility alias (deprecated, will be removed in v2.0)
CrossRefTransformer = CrossRefPublicationTransformer

__all__ = ["CrossRefPublicationTransformer", "CrossRefTransformer"]
