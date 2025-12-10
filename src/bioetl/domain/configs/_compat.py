"""Deprecated aliases for backward compatibility.

This module provides deprecated aliases that will be removed in v3.0.
All imports trigger DeprecationWarning with migration instructions.

Migration guide:
    - ClientConfig -> HttpClientConfig
    - HttpClientSettings -> ProviderHttpConfig
    - HttpClientDefaults -> HttpClientConfig
    - HTTP_CLIENT_DEFAULTS -> HttpClientConfig()
    - QcConfig -> QualityControlConfig
"""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from bioetl.domain.configs.pipeline import (
        HttpClientConfig,
        ProviderHttpConfig,
        QualityControlConfig,
    )

__all__ = [
    "ClientConfig",
    "HttpClientDefaults",
    "HttpClientSettings",
    "HTTP_CLIENT_DEFAULTS",
    "QcConfig",
]

# Mapping of deprecated names to (new_name, actual_import_path)
_DEPRECATED_ALIASES: dict[str, tuple[str, str]] = {
    "ClientConfig": ("HttpClientConfig", "bioetl.domain.configs.pipeline"),
    "HttpClientSettings": ("ProviderHttpConfig", "bioetl.domain.configs.pipeline"),
    "HttpClientDefaults": ("HttpClientConfig", "bioetl.domain.configs.pipeline"),
    "HTTP_CLIENT_DEFAULTS": ("HttpClientConfig()", "bioetl.domain.configs.pipeline"),
    "QcConfig": ("QualityControlConfig", "bioetl.domain.configs.pipeline"),
}


def _warn_deprecated(old_name: str, new_name: str, stacklevel: int = 4) -> None:
    """Emit deprecation warning for an alias.

    Args:
        old_name: The deprecated name being used.
        new_name: The recommended replacement name.
        stacklevel: Stack level for the warning. Default is 4 to account for:
            1. User code
            2. __init__.py __getattr__
            3. _compat.py __getattr__
            4. _warn_deprecated
    """
    warnings.warn(
        f"{old_name} is deprecated, use {new_name} instead. "
        "Will be removed in v3.0.",
        DeprecationWarning,
        stacklevel=stacklevel,
    )


def _get_http_client_config() -> type:
    """Lazy import HttpClientConfig."""
    from bioetl.domain.configs.pipeline import HttpClientConfig

    return HttpClientConfig


def _get_provider_http_config() -> type:
    """Lazy import ProviderHttpConfig."""
    from bioetl.domain.configs.pipeline import ProviderHttpConfig

    return ProviderHttpConfig


def _get_quality_control_config() -> type:
    """Lazy import QualityControlConfig."""
    from bioetl.domain.configs.pipeline import QualityControlConfig

    return QualityControlConfig


class _DeprecatedQcConfig:
    """Factory for QcConfig that emits deprecation warning on instantiation."""

    def __new__(cls, **data: Any) -> Any:
        # stacklevel=2: user code -> QcConfig() -> __new__
        _warn_deprecated("QcConfig", "QualityControlConfig", stacklevel=2)
        QualityControlConfig = _get_quality_control_config()
        return QualityControlConfig(**data)


class _DeprecatedHttpClientDefaults:
    """Factory for HttpClientDefaults that emits deprecation warning."""

    def __new__(cls, **data: Any) -> Any:
        # stacklevel=2: user code -> HttpClientDefaults() -> __new__
        _warn_deprecated("HttpClientDefaults", "HttpClientConfig", stacklevel=2)
        HttpClientConfig = _get_http_client_config()
        return HttpClientConfig(**data)


def __getattr__(name: str) -> Any:
    """Module-level __getattr__ for lazy loading with deprecation warnings.

    This enables deprecation warnings when deprecated aliases are imported
    or accessed, while maintaining backward compatibility.
    """
    if name == "ClientConfig":
        _warn_deprecated("ClientConfig", "HttpClientConfig")
        return _get_http_client_config()

    if name == "HttpClientSettings":
        _warn_deprecated("HttpClientSettings", "ProviderHttpConfig")
        return _get_provider_http_config()

    if name == "HttpClientDefaults":
        _warn_deprecated("HttpClientDefaults", "HttpClientConfig")
        return _DeprecatedHttpClientDefaults

    if name == "HTTP_CLIENT_DEFAULTS":
        _warn_deprecated("HTTP_CLIENT_DEFAULTS", "HttpClientConfig()")
        HttpClientConfig = _get_http_client_config()
        return HttpClientConfig()

    if name == "QcConfig":
        _warn_deprecated("QcConfig", "QualityControlConfig")
        return _DeprecatedQcConfig

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# For static type checking only
if TYPE_CHECKING:
    ClientConfig = HttpClientConfig
    HttpClientSettings = ProviderHttpConfig
    HttpClientDefaults = HttpClientConfig
    HTTP_CLIENT_DEFAULTS: HttpClientConfig
    QcConfig = QualityControlConfig
