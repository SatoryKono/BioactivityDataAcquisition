"""Semantic Scholar pipeline components.

Provides transformers and utilities for Semantic Scholar data processing.
"""

from bioetl.application.pipelines.semantic_scholar.transformer import (
    S2PublicationTransformer,
)

__all__ = ["S2PublicationTransformer"]
