"""UniProt provider adapter.

Implements RULES.md Appendix A - UniProt data source.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.uniprot.client import UniProtAdapter
from bioetl.infrastructure.adapters.uniprot.models import (
    UNIPROT_RECORD_MODELS,
    UniProtFeatureRecord,
    UniProtProteinRecord,
    UniProtSearchResponse,
    UniProtSequenceRecord,
)

__all__ = [
    "UNIPROT_RECORD_MODELS",
    "UniProtAdapter",
    "UniProtFeatureRecord",
    "UniProtProteinRecord",
    "UniProtSearchResponse",
    "UniProtSequenceRecord",
]
