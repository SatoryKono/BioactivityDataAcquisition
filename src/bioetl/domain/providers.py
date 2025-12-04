"""Provider domain abstractions and factories."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from bioetl.domain.normalization_service import NormalizationService


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
class ProviderComponents(Protocol):
    """Protocol describing provider component factories."""

    def create_client(self, config: BaseProviderConfig):
        """Create provider client instance."""

    def create_extraction_service(self, client: object, config: BaseProviderConfig):
        """Create provider-specific extraction service."""

    # Optional factories
    def create_normalization_service(
        self,
        config: BaseProviderConfig,
        *,
        client: object | None = None,
        pipeline_config: object | None = None,
    ) -> NormalizationService:  # pragma: no cover - optional
        """Create provider-specific normalization service."""

    def create_writer(self, config: BaseProviderConfig):  # pragma: no cover - optional
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
