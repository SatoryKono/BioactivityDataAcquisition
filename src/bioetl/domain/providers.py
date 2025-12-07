"""Provider domain abstractions and factories."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Generic, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, ConfigDict

from bioetl.domain.transform.contracts import NormalizationServiceABC

client_t_co = TypeVar("client_t_co", covariant=True)
extraction_service_t_co = TypeVar("extraction_service_t_co", covariant=True)
normalization_service_t_co = TypeVar(
    "normalization_service_t_co", bound=NormalizationServiceABC | None, covariant=True
)
writer_t_co = TypeVar("writer_t_co", covariant=True)


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
        client_t_co,
        extraction_service_t_co,
        normalization_service_t_co,
        writer_t_co,
    ],
    Generic[
        client_t_co,
        extraction_service_t_co,
        normalization_service_t_co,
        writer_t_co,
    ],
):
    """Protocol describing provider component factories with consistent signatures."""

    def create_client(self, config: BaseProviderConfig) -> client_t_co:
        """Create provider client instance."""

    def create_extraction_service(
        self,
        config: BaseProviderConfig,
        *,
        client: client_t_co | None = None,
    ) -> extraction_service_t_co:
        """Create provider-specific extraction service."""

    # Optional factories
    def create_normalization_service(
        self,
        config: BaseProviderConfig,
        *,
        client: client_t_co | None = None,
        pipeline_config: object | None = None,
    ) -> normalization_service_t_co:  # pragma: no cover - optional
        """Create provider-specific normalization service."""

    def create_writer(
        self,
        config: BaseProviderConfig,
        *,
        client: client_t_co | None = None,
    ) -> writer_t_co:  # pragma: no cover - optional
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
