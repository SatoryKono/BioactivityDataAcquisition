"""Preflight validation subpackage.

Pre-pipeline health checks, medallion config validation, and aggregation.
"""

from __future__ import annotations

from bioetl.application.core.preflight.service import *  # noqa: F403 - compatibility facade; explicit __all__ below
from bioetl.application.core.preflight.service import __all__ as _PREFLIGHT_EXPORTS

__all__ = _PREFLIGHT_EXPORTS
