"""Infrastructure adapters implementing application ports.

This module provides concrete implementations of application layer ports,
bridging the gap between abstract interfaces and infrastructure components.

Adapters defined here:
- ConfigLoaderAdapter: Implements ConfigLoaderPortABC
- ConfigPathResolverAdapter: Implements ConfigPathResolverPortABC
- ABCRegistryResolverAdapter: Implements ABCRegistryResolverPortABC
- PandasTabularAdapter: Implements TabularData for pandas DataFrames
"""

from bioetl.infrastructure.adapters.abc_registry_adapter import (
    ABCRegistryResolverAdapter,
)
from bioetl.infrastructure.adapters.config_loader_adapter import (
    ConfigLoaderAdapter,
    ConfigPathResolverAdapter,
)
from bioetl.infrastructure.adapters.pandas_tabular import (
    PandasTabularAdapter,
)

__all__ = [
    "ABCRegistryResolverAdapter",
    "ConfigLoaderAdapter",
    "ConfigPathResolverAdapter",
    "PandasTabularAdapter",
]
