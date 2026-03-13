"""Deprecated compatibility facade for base-transformer dependency typing.

Concrete default collaborator construction is composition-owned.
Application code should consume ``TransformerDependencyContext`` only.
"""

from __future__ import annotations

from bioetl.application.core.base_transformer.types import (
    TransformerDependencyContext,
)

__all__ = ["TransformerDependencyContext"]
