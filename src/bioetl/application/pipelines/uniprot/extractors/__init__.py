"""UniProt extraction components."""

from __future__ import annotations

from bioetl.application.pipelines.uniprot.extractors.comments import CommentExtractor
from bioetl.application.pipelines.uniprot.extractors.features import FeatureExtractor
from bioetl.application.pipelines.uniprot.extractors.gene import GeneExtractor
from bioetl.application.pipelines.uniprot.extractors.references import (
    ReferenceExtractor,
)

__all__ = [
    "CommentExtractor",
    "FeatureExtractor",
    "GeneExtractor",
    "ReferenceExtractor",
]
