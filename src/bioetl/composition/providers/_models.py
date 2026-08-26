"""Internal provider registry models and creator contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.ports import DataSourcePort

from bioetl.application.ports.providers import (
    AdapterCreatorProtocol,
    DataSourceCreatorProtocol,
    HttpConfig,
    ProviderSettingsProtocol,
    SecretValueProviderProtocol,
)


__all__ = [
    "AdapterCreatorProtocol",
    "DataSourceCreatorProtocol",
    "HttpConfig",
    "ProviderConfig",
    "ProviderSettingsProtocol",
    "SecretValueProviderProtocol",
]


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
