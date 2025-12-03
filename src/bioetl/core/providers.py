"""Provider abstractions and metadata definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, TypeVar

from pydantic import BaseModel

ProviderConfigT = TypeVar("ProviderConfigT", bound="BaseProviderConfig")
ProviderClientT = TypeVar("ProviderClientT")
ExtractionServiceT = TypeVar("ExtractionServiceT")


class ProviderId(str, Enum):
    """Canonical provider identifiers following PIPE-002."""

    CHEMBL = "chembl"
    PUBCHEM = "pubchem"
    UNIPROT = "uniprot"
    PUBMED = "pubmed"


class BaseProviderConfig(BaseModel):
    """Base class for provider-specific configuration models."""

    model_config = {
        "extra": "forbid",
    }


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


__all__ = [
    "BaseProviderConfig",
    "ProviderComponents",
    "ProviderDefinition",
    "ProviderId",
]
