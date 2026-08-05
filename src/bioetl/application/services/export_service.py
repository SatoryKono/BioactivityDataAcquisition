"""Compatibility re-export — implementation lives in `bioetl.application.services.export_lineage.export_service`.

ARCH-REF-03 / #7704: root path kept for stable imports.
"""
from __future__ import annotations

from bioetl.application.services.export_lineage.export_service import *  # noqa: F403
from bioetl.application.services.export_lineage.export_service import __all__ as __all__
