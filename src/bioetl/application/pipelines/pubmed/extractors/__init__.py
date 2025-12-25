"""PubMed XML extractors.

This package provides specialized extractors for parsing PubMed XML elements.
Each extractor is responsible for a single domain of data extraction.
"""

from __future__ import annotations

from bioetl.application.pipelines.pubmed.extractors.abstract import AbstractExtractor
from bioetl.application.pipelines.pubmed.extractors.author import AuthorExtractor
from bioetl.application.pipelines.pubmed.extractors.classification import (
    ClassificationExtractor,
)
from bioetl.application.pipelines.pubmed.extractors.date import DateExtractor
from bioetl.application.pipelines.pubmed.extractors.identifier import (
    IdentifierExtractor,
)

__all__ = [
    "AbstractExtractor",
    "AuthorExtractor",
    "ClassificationExtractor",
    "DateExtractor",
    "IdentifierExtractor",
]
