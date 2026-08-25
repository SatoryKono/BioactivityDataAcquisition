"""Neutral protocol contracts shared by provider-registry helpers."""

from __future__ import annotations

from bioetl.application.ports.providers import (
    ProviderDataSourceAccessProtocol,
    ProviderRegistrarProtocol,
)

__all__ = [
    "ProviderDataSourceAccessProtocol",
    "ProviderRegistrarProtocol",
]
