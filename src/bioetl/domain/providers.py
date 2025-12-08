"""Provider domain abstractions and factories."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Protocol, TypeVar, runtime_checkable

from pydantic import BaseModel, ConfigDict

if TYPE_CHECKING:
    from bioetl.domain.transform.contracts import NormalizationServiceABC

client_t = TypeVar("client_t")
extraction_service_t = TypeVar("extraction_service_t", covariant=True)
normalization_service_t = TypeVar(
    "normalization_service_t",
    bound="NormalizationServiceABC | None",
    covariant=True,
)
writer_t = TypeVar("writer_t", covariant=True)


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
        client_t,
        extraction_service_t,
        normalization_service_t,
        writer_t,
    ]
):
    """Protocol describing provider component factories with consistent signatures."""

    def create_client(self, config: BaseProviderConfig) -> client_t:
        """Create provider client instance."""

    def create_extraction_service(
        self,
        config: BaseProviderConfig,
        *,
        client: client_t | None = None,
    ) -> extraction_service_t:
        """Create provider-specific extraction service."""

    # Optional factories
    def create_normalization_service(
        self,
        config: BaseProviderConfig,
        *,
        client: client_t | None = None,
        pipeline_config: object | None = None,
    ) -> normalization_service_t:  # pragma: no cover - optional
        """Create provider-specific normalization service."""

    def create_writer(
        self,
        config: BaseProviderConfig,
        *,
        client: client_t | None = None,
    ) -> writer_t:  # pragma: no cover - optional
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
