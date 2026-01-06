"""UniProt data extractors package.

Provides specialized extractors for different aspects of UniProt data.
"""

from bioetl.application.pipelines.uniprot.extractors.comments import CommentExtractor
from bioetl.application.pipelines.uniprot.extractors.crossrefs import CrossRefExtractor
from bioetl.application.pipelines.uniprot.extractors.features import FeatureExtractor
from bioetl.application.pipelines.uniprot.extractors.genes import GeneExtractor
from bioetl.application.pipelines.uniprot.extractors.utils import ExtractorUtils

__all__ = [
    "CommentExtractor",
    "CrossRefExtractor",
    "ExtractorUtils",
    "FeatureExtractor",
    "GeneExtractor",
]
