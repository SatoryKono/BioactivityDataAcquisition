"""Compatibility facade for the export-lineage pipeline debug service.

ARCH-REF-03 / #7704: root path kept for stable imports.
"""

from __future__ import annotations

from bioetl.application.services.export_lineage.pipeline_debug_service import *  # noqa: F403
from bioetl.application.services.export_lineage.pipeline_debug_service import (
    DebugAbortError as DebugAbortError,
)
from bioetl.application.services.export_lineage.pipeline_debug_service import (
    __all__ as __all__,
)
