"""Common pipeline components.

This package contains shared base classes and utilities for publication transformers
that reduce code duplication across providers.

Main Components:
- BasePublicationTransformer: Template Method base for publication transformers
- extract_author_names: Universal author name extractor for pre-combined name fields
"""

from __future__ import annotations

from bioetl.application.pipelines.common.base_publication_transformer import (
    BasePublicationTransformer,
)
from bioetl.application.pipelines.common.extractors import extract_author_names

__all__ = [
    "BasePublicationTransformer",
    "extract_author_names",
]
