# mypy: disable-error-code="misc"
"""Pydantic models for CrossRef API responses.

These models provide type-safe parsing and validation for CrossRef REST API responses.
They are infrastructure-layer models (not domain models) for raw API data.

Documentation: https://api.crossref.org/swagger-ui/index.html

See RULES.md §8.2 for JSON response modeling guidelines.
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.crossref._publication_record import (
    CrossRefPublicationRecord,
)
from bioetl.infrastructure.adapters.crossref.models_shared import (
    CrossRefAssertion,
    CrossRefAuthor,
    CrossRefClinicalTrial,
    CrossRefDateParts,
    CrossRefFunder,
    CrossRefLicense,
    CrossRefLink,
    CrossRefReference,
)

if TYPE_CHECKING:
    import bioetl.infrastructure.adapters.crossref._response_models as _crossref_response_models

__all__ = [
    "CROSSREF_RECORD_MODELS",
    "CrossRefAssertion",
    "CrossRefAuthor",
    "CrossRefClinicalTrial",
    "CrossRefDateParts",
    "CrossRefFunder",
    "CrossRefLicense",
    "CrossRefLink",
    "CrossRefMessage",
    "CrossRefPublicationRecord",
    "CrossRefPublicationResponse",
    "CrossRefPublicationsResponse",
    "CrossRefReference",
]

CrossRefMessage: type[_crossref_response_models.CrossRefMessage]
CrossRefPublicationResponse: type[_crossref_response_models.CrossRefPublicationResponse]
CrossRefPublicationsResponse: type[
    _crossref_response_models.CrossRefPublicationsResponse
]


# === Record Type Mapping ===
CROSSREF_RECORD_MODELS: dict[str, type[BaseModel]] = {
    "work": CrossRefPublicationRecord,
    "publication": CrossRefPublicationRecord,
}

# Load response wrappers only after CrossRefPublicationRecord exists.
_response_models = importlib.import_module(
    "bioetl.infrastructure.adapters.crossref._response_models"
)
CrossRefMessage = _response_models.CrossRefMessage
CrossRefPublicationResponse = _response_models.CrossRefPublicationResponse
CrossRefPublicationsResponse = _response_models.CrossRefPublicationsResponse
_record_namespace = {
    "Any": Any,  # Any: Required for pydantic model_rebuild dynamic type resolution
    "CrossRefPublicationRecord": CrossRefPublicationRecord,
    "JsonDict": JsonDict,
}
CrossRefMessage.model_rebuild(_types_namespace=_record_namespace)
CrossRefPublicationResponse.model_rebuild(_types_namespace=_record_namespace)
CrossRefPublicationsResponse.model_rebuild(_types_namespace=_record_namespace)
