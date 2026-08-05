"""Compatibility re-export — implementation lives in `bioetl.application.services.quality._quarantine_service_sync_support`.

ARCH-REF-03 / #7704: root path kept for stable imports.
"""
from __future__ import annotations

from bioetl.application.services.quality._quarantine_service_sync_support import *  # noqa: F403
from bioetl.application.services.quality._quarantine_service_sync_support import __all__ as __all__
