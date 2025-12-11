"""Configuration migration utilities.

.. deprecated::
    This module has been moved to ``bioetl.infrastructure.config.migration``.
    Import from the new location instead::

        from bioetl.infrastructure.config.migration import ConfigMigrator

    This module is kept for backward compatibility and will emit a
    DeprecationWarning when ConfigMigrator is accessed.
    It will be removed in a future release.

The migrator handles migration of legacy pipeline configuration formats
to the current structure. See the new module for full documentation.
"""

from __future__ import annotations

import importlib
from typing import Any
import warnings


def __getattr__(name: str) -> Any:
    if name == "ConfigMigrator":
        warnings.warn(
            "Importing ConfigMigrator from bioetl.domain.configs.migration is "
            "deprecated. Import from the infrastructure layer instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        mod = importlib.import_module(".".join(["bioetl", "infrastructure", "config", "migration"]))
        return getattr(mod, "ConfigMigrator")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ConfigMigrator available via __getattr__ for backward compatibility
__all__: list[str] = []
