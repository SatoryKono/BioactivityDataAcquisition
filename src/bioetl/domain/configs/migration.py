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

import warnings
from typing import TYPE_CHECKING, Any

# Re-export ConfigMigrator from infrastructure layer with deprecation warning
# This maintains backward compatibility for existing imports

_deprecation_warning_emitted = False


def __getattr__(name: str) -> Any:
    """Lazy loading with deprecation warning for ConfigMigrator."""
    global _deprecation_warning_emitted

    if name == "ConfigMigrator":
        if not _deprecation_warning_emitted:
            warnings.warn(
                "Importing ConfigMigrator from bioetl.domain.configs.migration is "
                "deprecated. Import from bioetl.infrastructure.config.migration "
                "instead. This module will be removed in a future release.",
                DeprecationWarning,
                stacklevel=2,
            )
            _deprecation_warning_emitted = True

        from bioetl.infrastructure.config.migration import ConfigMigrator

        return ConfigMigrator

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# For static type checking, provide type hint
if TYPE_CHECKING:
    from bioetl.infrastructure.config.migration import (
        ConfigMigrator as ConfigMigrator,
    )


__all__ = ["ConfigMigrator"]
