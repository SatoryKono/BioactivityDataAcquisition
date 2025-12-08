"""Normalization config provider protocol for interfaces layer."""

from __future__ import annotations

from typing import Any, Protocol


class NormalizationConfigProviderProtocol(Protocol):
    """Provides normalization configuration and field metadata."""

    def get_normalization(self) -> Any:
        """Return normalization section."""

    def get_fields(self) -> list[dict[str, Any]]:
        """Return fields configuration."""


__all__ = ["NormalizationConfigProviderProtocol"]
