"""UniProt data extractors package.

Provides specialized extractors for different aspects of UniProt data.
"""

from __future__ import annotations

from bioetl.application.pipelines.uniprot.extractors._comment_facets_data import (
    _COMMENT_ANNOTATION_OUTPUT_KEYS,
)
from bioetl.application.pipelines.uniprot.extractors.comments import CommentExtractor
from bioetl.application.pipelines.uniprot.extractors.crossrefs import CrossRefExtractor
from bioetl.application.pipelines.uniprot.extractors.extractor_helpers import (
    ExtractorHelper,
)
from bioetl.application.pipelines.uniprot.extractors.features import FeatureExtractor
from bioetl.application.pipelines.uniprot.extractors.genes import GeneExtractor
from bioetl.application.pipelines.uniprot.extractors.taxonomy import TaxonomyExtractor

__all__ = [
    "_COMMENT_ANNOTATION_OUTPUT_KEYS",
    "CommentExtractor",
    "CrossRefExtractor",
    "ExtractorHelper",
    "FeatureExtractor",
    "GeneExtractor",
    "TaxonomyExtractor",
]
