"""
UniProt data extractors.
"""

from bioetl.application.pipelines.uniprot.extractors.abstract import AbstractExtractor
from bioetl.application.pipelines.uniprot.extractors.author import AuthorExtractor
from bioetl.application.pipelines.uniprot.extractors.classification import (
    ClassificationExtractor,
)
from bioetl.application.pipelines.uniprot.extractors.comments import CommentExtractor
from bioetl.application.pipelines.uniprot.extractors.crossref import CrossRefExtractor
from bioetl.application.pipelines.uniprot.extractors.date import DateExtractor
from bioetl.application.pipelines.uniprot.extractors.extractor_utils import (
    ExtractorUtils,
)
from bioetl.application.pipelines.uniprot.extractors.features import FeatureExtractor
from bioetl.application.pipelines.uniprot.extractors.gene import GeneExtractor
from bioetl.application.pipelines.uniprot.extractors.identifier import (
    IdentifierExtractor,
)
from bioetl.application.pipelines.uniprot.extractors.keywords import KeywordExtractor
from bioetl.application.pipelines.uniprot.extractors.organism import OrganismExtractor
from bioetl.application.pipelines.uniprot.extractors.references import (
    ReferenceExtractor,
)
from bioetl.application.pipelines.uniprot.extractors.sequence import SequenceExtractor
from bioetl.application.pipelines.uniprot.extractors.taxonomy import TaxonomyExtractor

__all__ = [
    "AbstractExtractor",
    "AuthorExtractor",
    "ClassificationExtractor",
    "CommentExtractor",
    "CrossRefExtractor",
    "DateExtractor",
    "ExtractorUtils",
    "FeatureExtractor",
    "GeneExtractor",
    "IdentifierExtractor",
    "KeywordExtractor",
    "OrganismExtractor",
    "ReferenceExtractor",
    "SequenceExtractor",
    "TaxonomyExtractor",
]
