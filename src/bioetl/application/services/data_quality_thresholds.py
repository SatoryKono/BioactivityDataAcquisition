"""Compatibility re-export — implementation lives in `bioetl.application.services.quality.data_quality_thresholds`.

ARCH-REF-03 / #7704: root path kept for stable imports.
"""
from __future__ import annotations

from bioetl.application.services.quality.data_quality_thresholds import *  # noqa: F403
from bioetl.application.services.quality.data_quality_thresholds import __all__ as __all__
