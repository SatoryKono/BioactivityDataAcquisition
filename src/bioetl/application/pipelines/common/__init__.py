"""Common pipeline components.

This package contains shared base classes and utilities for publication transformers
that reduce code duplication across providers.

Main Components:
- BasePublicationTransformer: Template Method base for publication transformers
- AuthorTransformMixin: Author normalization helpers
- DateTransformMixin: Date parsing and validation helpers
- IdentifierTransformMixin: DOI/PMID validation and metadata helpers
- extract_author_names: Universal author name extractor for pre-combined name fields
"""

from __future__ import annotations

from bioetl.application.pipelines.common.author_transform_mixin import (
    AuthorTransformMixin,
)
from bioetl.application.pipelines.common.base_publication_transformer import (
    BasePublicationTransformer,
)
from bioetl.application.pipelines.common.date_transform_mixin import (
    DateTransformMixin,
)
from bioetl.application.pipelines.common.extractors import extract_author_names
from bioetl.application.pipelines.common.identifier_transform_mixin import (
    IdentifierTransformMixin,
)

__all__ = [
    "AuthorTransformMixin",
    "BasePublicationTransformer",
    "DateTransformMixin",
    "IdentifierTransformMixin",
    "extract_author_names",
]
