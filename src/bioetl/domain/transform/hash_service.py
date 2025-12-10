"""DEPRECATED: HashService moved to infrastructure layer.

This module is kept for backward compatibility only.
Use bioetl.infrastructure.transform.impl.hash_service.Blake2bHashService instead.

For the abstract interface, use bioetl.domain.transform.contracts.HashServiceABC.
"""

from __future__ import annotations

import warnings

# Re-export for backward compatibility
from bioetl.infrastructure.transform.impl.hash_service import (
    Blake2bHashService as HashService,
)

warnings.warn(
    "bioetl.domain.transform.hash_service is deprecated. "
    "Use bioetl.infrastructure.transform.impl.hash_service.Blake2bHashService instead. "
    "For the ABC, use bioetl.domain.transform.contracts.HashServiceABC.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["HashService"]
