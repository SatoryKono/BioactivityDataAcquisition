# mypy: disable-error-code="misc"
"""Pydantic models for PubMed API responses.

These models provide type-safe parsing and validation for PubMed data.
They are infrastructure-layer models (not domain models) for parsed XML records.

Note: PubMed returns XML responses which are parsed by PubMedXmlProcessor.
These models validate the dictionary representation after XML parsing.

Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25499/

See RULES.md §8.2 for JSON response modeling guidelines.
"""

from __future__ import annotations

import typing

from pydantic import BaseModel, ConfigDict, Field

import bioetl.infrastructure.adapters.pubmed._article_components as components
from bioetl.infrastructure.adapters.pubmed._extended_record import (
    PubMedExtendedRecord,
)
from bioetl.infrastructure.adapters.pubmed._search_models import (
    PubMedSearchResponse,
    PubMedSearchResult,
)

__all__ = [
    "PubMedArticleRecord",
    "PubMedExtendedRecord",
    "PubMedSearchResponse",
    "PubMedSearchResult",
    *components.ARTICLE_COMPONENT_NAMES,
]
# Let's keep original order for safety
__all__ = sorted(__all__)


def __getattr__(name: str) -> typing.Any:  # Any: module level magic method returns Any
    if name in components.ARTICLE_COMPONENT_NAMES:
        return getattr(components, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return __all__


# === Basic Record Model (matches current xml_processor output) ===


class PubMedArticleRecord(BaseModel):
    """Basic article record from PubMed XML parsing.

    Matches the output of PubMedXmlProcessor.extract_record().
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Primary Key
    pmid: str | None = Field(default=None, description="PubMed ID")

    # Article Content
    article_title: str = Field(default="No title found", description="Article title")

    # Raw XML for forensic analysis (uses underscore prefix in source data)
    raw_xml: str | None = Field(
        default=None, alias="_raw_xml", description="Raw XML content"
    )


# === Record Type Mapping ===

PUBMED_RECORD_MODELS: dict[str, type[BaseModel]] = {
    "publication": PubMedArticleRecord,
    "publication_extended": PubMedExtendedRecord,
}
