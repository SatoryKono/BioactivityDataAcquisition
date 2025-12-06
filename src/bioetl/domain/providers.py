"""Provider domain abstractions and factories."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Generic, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, ConfigDict

from bioetl.domain.transform.contracts import NormalizationServiceABC

ClientT_co = TypeVar("ClientT_co", covariant=True)
ExtractionServiceT_co = TypeVar("ExtractionServiceT_co", covariant=True)
NormalizationServiceT_co = TypeVar(
    "NormalizationServiceT_co", bound=NormalizationServiceABC | None, covariant=True
)
WriterT_co = TypeVar("WriterT_co", covariant=True)


class ProviderId(str, Enum):
    """Canonical provider identifiers."""

    CHEMBL = "chembl"
    PUBCHEM = "pubchem"
    UNIPROT = "uniprot"
    PUBMED = "pubmed"
    DUMMY = "dummy"


class BaseProviderConfig(BaseModel):
    """Base provider configuration model."""

    model_config = ConfigDict(extra="forbid")


@runtime_checkable
class ProviderComponents(
    Protocol[
        ClientT_co,
        ExtractionServiceT_co,
        NormalizationServiceT_co,
        WriterT_co,
    ],
    Generic[
        ClientT_co,
        ExtractionServiceT_co,
        NormalizationServiceT_co,
        WriterT_co,
    ],
):
    """Protocol describing provider component factories with consistent signatures."""

    def create_client(self, config: BaseProviderConfig) -> ClientT_co:
        """Create provider client instance."""

    def create_extraction_service(
        self,
        config: BaseProviderConfig,
        *,
        client: ClientT_co | None = None,
    ) -> ExtractionServiceT_co:
        """Create provider-specific extraction service."""

    # Optional factories
    def create_normalization_service(
        self,
        config: BaseProviderConfig,
        *,
        client: ClientT_co | None = None,
        pipeline_config: object | None = None,
    ) -> NormalizationServiceT_co:  # pragma: no cover - optional
        """Create provider-specific normalization service."""

    def create_writer(
        self,
        config: BaseProviderConfig,
        *,
        client: ClientT_co | None = None,
    ) -> WriterT_co:  # pragma: no cover - optional
        """Create provider-specific writer."""


@dataclass(frozen=True)
class ProviderDefinition:
    """Provider metadata and factory entry points."""

    id: ProviderId
    config_type: type[BaseProviderConfig]
    components: ProviderComponents
    description: str | None = None


__all__ = [
    "BaseProviderConfig",
    "ProviderComponents",
    "ProviderDefinition",
    "ProviderId",
]
