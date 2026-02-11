"""
UniProt data extractors.
"""

from bioetl.application.pipelines.uniprot.extractors.abstract import AbstractExtractor
from bioetl.application.pipelines.uniprot.extractors.comments import CommentExtractor
from bioetl.application.pipelines.uniprot.extractors.crossref import CrossRefExtractor
from bioetl.application.pipelines.uniprot.extractors.extractor_utils import (
    ExtractorUtils,
)
from bioetl.application.pipelines.uniprot.extractors.features import FeatureExtractor
from bioetl.application.pipelines.uniprot.extractors.gene import GeneExtractor
from bioetl.application.pipelines.uniprot.extractors.taxonomy import TaxonomyExtractor

__all__ = [
    "AbstractExtractor",
    "CommentExtractor",
    "CrossRefExtractor",
    "ExtractorUtils",
    "FeatureExtractor",
    "GeneExtractor",
    "TaxonomyExtractor",
]
