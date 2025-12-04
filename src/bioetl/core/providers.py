"""Provider domain abstractions and factories."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel

ProviderConfigT = TypeVar("ProviderConfigT", bound=BaseModel)
ProviderClientT = TypeVar("ProviderClientT")
ExtractionServiceT = TypeVar("ExtractionServiceT")


class ProviderId(str, Enum):
    """Canonical provider identifiers."""

    CHEMBL = "chembl"
    PUBCHEM = "pubchem"
    UNIPROT = "uniprot"
    PUBMED = "pubmed"
    DUMMY = "dummy"


@runtime_checkable
class ProviderComponents(Protocol[ProviderConfigT, ProviderClientT, ExtractionServiceT]):
    """Protocol describing provider component factories."""

    def create_client(self, config: ProviderConfigT) -> ProviderClientT:
        """Create provider client instance."""

    def create_extraction_service(
        self, client: ProviderClientT, config: ProviderConfigT
    ) -> ExtractionServiceT:
        """Create provider-specific extraction service."""


@dataclass(frozen=True)
class ProviderDefinition:
    """Provider metadata and factory entry points."""

    id: ProviderId
    config_type: type[ProviderConfigT]
    components: ProviderComponents[ProviderConfigT, ProviderClientT, ExtractionServiceT]
    description: str | None = None


__all__ = ["ProviderComponents", "ProviderDefinition", "ProviderId"]
