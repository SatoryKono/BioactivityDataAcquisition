"""Compatibility re-export — implementation lives in `bioetl.application.services.export_lineage.export_manifest_identity`.

ARCH-REF-03 / #7704: root path kept for stable imports.
"""
from __future__ import annotations

from bioetl.application.services.export_lineage.export_manifest_identity import *  # noqa: F403
from bioetl.application.services.export_lineage.export_manifest_identity import __all__ as __all__
