"""Composition services for cross-cutting concerns.

Import owner modules directly for service implementations. This package keeps
only the ``versioning`` submodule namespace.
"""

from __future__ import annotations

from . import versioning

__all__ = ["versioning"]
