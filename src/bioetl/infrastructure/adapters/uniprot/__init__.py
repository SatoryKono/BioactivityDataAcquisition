"""UniProt provider adapter.

Implements RULES.md Appendix A - UniProt data source.
"""

from __future__ import annotations

from bioetl.infrastructure.adapters.uniprot.client import UniProtAdapter
from bioetl.infrastructure.adapters.uniprot.idmapping_client import (
    IDMappingJobError,
    IDMappingTimeoutError,
    UniProtIDMappingClient,
)
from bioetl.infrastructure.adapters.uniprot.models import (
    UNIPROT_RECORD_MODELS,
    UniProtFeatureRecord,
    UniProtProteinRecord,
    UniProtSearchResponse,
    UniProtSequenceRecord,
)

__all__ = [
    # Model Mappings
    "UNIPROT_RECORD_MODELS",
    # Adapters
    "UniProtAdapter",
    "UniProtIDMappingClient",
    # ID Mapping Exceptions
    "IDMappingJobError",
    "IDMappingTimeoutError",
    # Record Models
    "UniProtFeatureRecord",
    "UniProtProteinRecord",
    # Response Models
    "UniProtSearchResponse",
    "UniProtSequenceRecord",
]
