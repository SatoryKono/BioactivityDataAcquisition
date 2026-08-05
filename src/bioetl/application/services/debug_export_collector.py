"""Compatibility re-export — implementation lives in `bioetl.application.services.export_lineage.debug_export_collector`.

ARCH-REF-03 / #7704: root path kept for stable imports.
"""
from __future__ import annotations

from bioetl.application.services.export_lineage.debug_export_collector import *  # noqa: F403
from bioetl.application.services.export_lineage.debug_export_collector import __all__ as __all__
