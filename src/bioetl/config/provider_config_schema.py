"""Provider configuration schemas with strict validation."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AnyHttpUrl, ConfigDict, Field, PositiveFloat, PositiveInt
from pydantic.types import NonNegativeInt

from bioetl.domain.providers import BaseProviderConfig as ProviderConfigBase


class BaseProviderConfig(ProviderConfigBase):
    """Базовая строгая конфигурация провайдера."""

    provider: Literal["chembl", "pubchem", "uniprot", "dummy"]
    base_url: AnyHttpUrl
    timeout_sec: PositiveFloat
    max_retries: NonNegativeInt
    rate_limit_per_sec: PositiveFloat | None = None

    model_config = ConfigDict(extra="forbid")


class ChemblSourceConfig(BaseProviderConfig):
    """Конфигурация источника ChEMBL."""

    provider: Literal["chembl"] = "chembl"
    api_version: str | None = None
    max_url_length: PositiveInt | None = None
    page_size: PositiveInt | None = None
    batch_size: PositiveInt | None = None

    model_config = ConfigDict(extra="forbid")

    def resolve_effective_batch_size(
        self, limit: int | None = None, hard_cap: int | None = 25
    ) -> int:
        """Вычисляет эффективный размер батча с учётом ограничений."""

        effective_batch = self.batch_size or hard_cap or 25

        if hard_cap is not None:
            effective_batch = min(effective_batch, hard_cap)

        if limit is not None:
            effective_batch = min(effective_batch, limit)

        return effective_batch


class DummyProviderConfig(BaseProviderConfig):
    """Конфигурация фиктивного провайдера для тестов и шаблонов."""

    provider: Literal["dummy"] = "dummy"


ProviderConfigUnion = Annotated[
    ChemblSourceConfig | DummyProviderConfig,
    Field(discriminator="provider"),
]

__all__ = [
    "BaseProviderConfig",
    "ChemblSourceConfig",
    "DummyProviderConfig",
    "ProviderConfigUnion",
]
