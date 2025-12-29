"""PubMed XML extractors.

This package provides specialized extractors for parsing PubMed XML elements.
Each extractor is responsible for a single domain of data extraction.

All extractors inherit from BaseFieldExtractor which implements the Template Method
pattern with extract() -> normalize() -> process() sequence.
"""

from __future__ import annotations

from bioetl.application.pipelines.pubmed.extractors.abstract import AbstractExtractor
from bioetl.application.pipelines.pubmed.extractors.author import AuthorExtractor
from bioetl.application.pipelines.pubmed.extractors.base import BaseFieldExtractor
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
    "BaseFieldExtractor",
    "ClassificationExtractor",
    "DateExtractor",
    "IdentifierExtractor",
]
