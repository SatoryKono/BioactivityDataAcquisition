"""Internal provider registry models and creator contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import DataSourcePort

from bioetl.application.ports.providers import AdapterCreatorProtocol
from bioetl.application.ports.providers import DataSourceCreatorProtocol
from bioetl.application.ports.providers import ProviderSettingsProtocol
from bioetl.application.ports.providers import SecretValueProviderProtocol


__all__ = [
    "AdapterCreatorProtocol",
    "DataSourceCreatorProtocol",
    "HttpConfig",
    "ProviderConfig",
    "ProviderSettingsProtocol",
    "SecretValueProviderProtocol",
]


@dataclass(frozen=True)
class HttpConfig:
    """HTTP client configuration for a provider."""

    rate: float = 5.0
    capacity: int = 10


@dataclass(frozen=True)
class ProviderConfig:
    """Complete provider configuration used by the composition registry."""

    adapter_class: type[DataSourcePort]
    http_config: HttpConfig | None = None
    requires_http_client: bool = True
    requires_logger: bool = True
    default_kwargs: dict[str, object] = field(default_factory=dict)
    adapter_creator: AdapterCreatorProtocol | None = None
    data_source_creator: DataSourceCreatorProtocol | None = None
